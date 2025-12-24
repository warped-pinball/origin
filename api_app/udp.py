import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable, Protocol, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models
from .database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# The Pico 2W boards broadcast discovery messages on this port
DISCOVERY_PORT = 37020
# Game state updates are broadcast separately on this port
GAME_STATE_PORT = 6809


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


_uid_fetch_cache: dict[str, tuple[datetime, str | None]] = {}
_version_fetch_cache: dict[str, tuple[datetime, str | None]] = {}
_machine_locks: dict[str, asyncio.Lock] = {}

# Delay between UID fetch attempts for the same IP when the last fetch failed
UID_FETCH_FAILURE_COOLDOWN_SECONDS = 60
VERSION_FETCH_COOLDOWN_SECONDS = 5 * 60


class MessageType:
    HELLO = 1
    FULL = 2
    PING = 3
    PONG = 4
    OFFLINE = 5


class DiscoveryMessage:
    """Structured discovery message with compact binary encoding."""

    __slots__ = ("type", "name", "peers", "ip")

    def __init__(
        self,
        mtype: int,
        name: bytes | None = None,
        peers: Iterable[Tuple[bytes, bytes]] | None = None,
        ip: bytes | None = None,
    ) -> None:
        self.type = mtype
        self.name = name
        self.peers = peers
        self.ip = ip

    @classmethod
    def hello(cls, name: bytes) -> "DiscoveryMessage":
        return cls(MessageType.HELLO, name=name)

    def encode(self) -> bytes:
        if self.type == MessageType.HELLO and self.name is not None:
            name_bytes = self.name[:255]
            return bytes([MessageType.HELLO, len(name_bytes)]) + name_bytes
        raise ValueError("Unsupported encoding")

    @staticmethod
    def decode(data: bytes):
        if not data:
            return None

        mtype = data[0]
        if mtype == MessageType.HELLO:
            if len(data) < 2:
                return None
            name_len = data[1]
            name = data[2 : 2 + name_len]
            return DiscoveryMessage(MessageType.HELLO, name=name)

        if mtype == MessageType.FULL:
            if len(data) < 2:
                return None
            count = data[1]

            def peer_gen():
                offset = 2
                for _ in range(count):
                    if len(data) < offset + 5:
                        return
                    ip_part = data[offset : offset + 4]
                    offset += 4
                    name_len = data[offset]
                    offset += 1
                    name = data[offset : offset + name_len]
                    offset += name_len
                    yield ip_part, name

            return DiscoveryMessage(MessageType.FULL, peers=peer_gen())

        if mtype in (MessageType.PING, MessageType.PONG):
            return DiscoveryMessage(mtype)

        if mtype == MessageType.OFFLINE and len(data) >= 5:
            return DiscoveryMessage(MessageType.OFFLINE, ip=data[1:5])

        return None


def _ip_bytes_to_str(ip_bytes: bytes) -> str:
    return ".".join(str(part) for part in ip_bytes)


def _normalize_machine_name(name: str | None) -> str | None:
    if name:
        stripped = name.strip()
        if stripped:
            return stripped
    return None


def _machine_lock(key: str) -> asyncio.Lock:
    if key not in _machine_locks:
        _machine_locks[key] = asyncio.Lock()
    return _machine_locks[key]


async def _fetch_machine_uid(
    ip_address: str,
    attempts: int = 2,
) -> str | None:
    url = f"http://{ip_address}/api/uid"
    last_error: Exception | None = None
    now = _utcnow()
    cached = _uid_fetch_cache.get(ip_address)
    if cached:
        cached_at, cached_uid = cached
        age = (now - cached_at).total_seconds()
        if cached_uid:
            logger.debug(
                "Using cached UID %s for %s from %.1fs ago", cached_uid, ip_address, age
            )
            return cached_uid
        if age < UID_FETCH_FAILURE_COOLDOWN_SECONDS:
            logger.info(
                "Skipping UID fetch for %s; last failure %.1fs ago (cooldown %ss)",
                ip_address,
                age,
                UID_FETCH_FAILURE_COOLDOWN_SECONDS,
            )
            return None

    for attempt in range(1, attempts + 1):
        logger.info("Fetching UID from %s (attempt %s/%s)", url, attempt, attempts)
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                logger.debug(
                    "UID fetch attempt %s status %s headers=%s", attempt, response.status_code, response.headers
                )
                response.raise_for_status()
                payload = response.json()
                uid = payload.get("uid")
                if uid:
                    _uid_fetch_cache[ip_address] = (_utcnow(), uid)
                    logger.info(
                        "Fetched UID %s from %s on attempt %s", uid, url, attempt
                    )
                    return uid
                logger.warning("UID response missing 'uid' key from %s: %s", url, payload)
        except Exception as exc:  # pragma: no cover - network errors
            last_error = exc
            logger.warning("Failed to fetch UID from %s on attempt %s/%s: %s", url, attempt, attempts, exc)

    if last_error:
        logger.error("Giving up fetching UID from %s after %s attempts: %s", url, attempts, last_error)
    else:
        logger.error("Giving up fetching UID from %s after %s attempts with empty responses", url, attempts)
    _uid_fetch_cache[ip_address] = (_utcnow(), None)
    return None


async def _fetch_machine_version(ip_address: str, attempts: int = 2) -> str | None:
    url = f"http://{ip_address}/api/version"
    last_error: Exception | None = None
    now = _utcnow()
    cached = _version_fetch_cache.get(ip_address)
    if cached:
        cached_at, cached_version = cached
        age = (now - cached_at).total_seconds()
        if age < VERSION_FETCH_COOLDOWN_SECONDS:
            logger.info(
                "Skipping version fetch for %s; last attempt %.1fs ago (cooldown %ss)",
                ip_address,
                age,
                VERSION_FETCH_COOLDOWN_SECONDS,
            )
            return cached_version

    for attempt in range(1, attempts + 1):
        logger.info(
            "Fetching version from %s (attempt %s/%s)", url, attempt, attempts
        )
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                logger.debug(
                    "Version fetch attempt %s status %s headers=%s", attempt, response.status_code, response.headers
                )
                response.raise_for_status()
                payload = response.json()
                version = payload.get("version")
                _version_fetch_cache[ip_address] = (_utcnow(), version)
                if version:
                    logger.info("Fetched version %s from %s on attempt %s", version, url, attempt)
                    return version
                logger.warning("Version response missing 'version' key from %s: %s", url, payload)
        except Exception as exc:  # pragma: no cover - network errors
            last_error = exc
            logger.warning(
                "Failed to fetch version from %s on attempt %s/%s: %s", url, attempt, attempts, exc
            )

    if last_error:
        logger.error(
            "Giving up fetching version from %s after %s attempts: %s", url, attempts, last_error
        )
    else:
        logger.error(
            "Giving up fetching version from %s after %s attempts with empty responses", url, attempts
        )

    _version_fetch_cache[ip_address] = (_utcnow(), None)
    return None


async def _get_active_game(db: AsyncSession, machine: models.Machine) -> models.Game | None:
    result = await db.execute(
        select(models.Game)
        .where(models.Game.machine_id == machine.id, models.Game.is_active.is_(True))
        .order_by(models.Game.start_time.desc(), models.Game.id.desc())
    )
    games = result.scalars().all()
    if not games:
        return None

    primary = games[0]
    if len(games) > 1:
        now = _utcnow()
        for extra in games[1:]:
            extra.is_active = False
            extra.end_time = extra.end_time or now
        await db.flush()

    return primary


async def _ensure_active_game(db: AsyncSession, machine: models.Machine) -> models.Game:
    existing = await _get_active_game(db, machine)
    if existing:
        return existing

    game = models.Game(machine=machine, is_active=True)
    db.add(game)
    await db.flush()
    return game


async def _deactivate_active_game(db: AsyncSession, machine: models.Machine) -> None:
    active = await _get_active_game(db, machine)
    if active:
        active.is_active = False
        active.end_time = _utcnow()


async def _upsert_machine(
    db: AsyncSession, ip_address: str, name: str | None, *, commit: bool = True
) -> models.Machine | None:
    logger.info(
        "Upserting machine from discovery ip=%s raw_name=%s", ip_address, name if name is not None else "<missing>"
    )
    uid = await _fetch_machine_uid(ip_address)
    if not uid:
        logger.info("Skipping machine at %s until UID is available", ip_address)
        return None

    display_name = _normalize_machine_name(name)
    if not display_name:
        logger.info("Skipping machine %s with missing name", uid)
        return None

    result = await db.execute(select(models.Machine).where(models.Machine.uid == uid))
    machine = result.scalars().first()

    now = _utcnow()
    if machine:
        machine.ip_address = ip_address
        machine.last_seen = now
        if machine.name != display_name:
            machine.name = display_name
        logger.info(
            "Updated machine id=%s uid=%s name=%s ip=%s last_seen=%s",
            machine.id,
            machine.uid,
            machine.name,
            machine.ip_address,
            machine.last_seen,
        )
    else:
        machine = models.Machine(
            name=display_name,
            ip_address=ip_address,
            uid=uid,
            last_seen=now,
        )
        db.add(machine)
        await db.flush()
        logger.info(
            "Created machine id=%s uid=%s name=%s ip=%s last_seen=%s",
            machine.id,
            machine.uid,
            machine.name,
            machine.ip_address,
            machine.last_seen,
        )

    await db.flush()
    await _maybe_refresh_version(db, machine)
    if commit:
        await db.commit()

    return machine


async def _get_or_create_machine_by_uid(
    db: AsyncSession,
    ip_address: str,
    machine_uid: str | None,
    *,
    machine_name: str | None = None,
) -> models.Machine | None:
    """Resolve a machine by UID (preferred) or create a placeholder entry.

    When handling game-state packets we already receive a UID, so we should not
    reach back to the board over HTTP just to rediscover it. If a machine entry
    is missing, create a basic record so we can still persist live scores.
    """

    machine = None
    if machine_uid:
        uid_result = await db.execute(
            select(models.Machine).where(models.Machine.uid == machine_uid)
        )
        machine = uid_result.scalars().first()

    if machine is None:
        ip_result = await db.execute(
            select(models.Machine).where(models.Machine.ip_address == ip_address)
        )
        machine = ip_result.scalars().first()

    now = _utcnow()

    if machine:
        if machine_uid and machine.uid != machine_uid:
            machine.uid = machine_uid
        machine.ip_address = ip_address
        machine.last_seen = now
        new_name = _normalize_machine_name(machine_name)
        if new_name and machine.name != new_name:
            machine.name = new_name
        await _maybe_refresh_version(db, machine)
        await db.flush()
        return machine

    if not machine_uid:
        # Fall back to the discovery path which will try to fetch a UID.
        return await _upsert_machine(db, ip_address, machine_name, commit=False)

    display_name = _normalize_machine_name(machine_name) or f"Machine {machine_uid}"
    machine = models.Machine(
        name=display_name,
        uid=machine_uid,
        ip_address=ip_address,
        last_seen=now,
    )
    db.add(machine)
    await db.flush()
    await _maybe_refresh_version(db, machine)
    return machine


async def _maybe_refresh_version(db: AsyncSession, machine: models.Machine) -> None:
    now = _utcnow()
    last_checked = _ensure_utc(machine.version_checked_at)
    if last_checked:
        age = (now - last_checked).total_seconds()
        if age < VERSION_FETCH_COOLDOWN_SECONDS:
            logger.debug(
                "Version for uid=%s checked %.1fs ago; skipping refresh", machine.uid, age
            )
            return

    version = await _fetch_machine_version(machine.ip_address)
    machine.version_checked_at = _utcnow()
    if version:
        machine.version = version
        logger.info(
            "Recorded machine version %s for uid=%s ip=%s", version, machine.uid, machine.ip_address
        )
    else:
        logger.warning(
            "Unable to resolve version for uid=%s ip=%s", machine.uid, machine.ip_address
        )
    db.add(machine)
    await db.flush()


async def ingest_discovery(
    db: AsyncSession,
    ip: str,
    *,
    name: str | None,
    peers: Iterable[tuple[str, str]] = (),
) -> None:
    if name:
        async with _machine_lock(ip):
            machine = await _upsert_machine(db, ip, name, commit=False)
            if machine:
                await _ensure_active_game(db, machine)
                await db.commit()
            return

    for peer_ip, peer_name in peers:
        async with _machine_lock(peer_ip):
            machine = await _upsert_machine(db, peer_ip, peer_name, commit=False)
            if machine:
                await _ensure_active_game(db, machine)
    await db.commit()


def _coerce_score(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalize_scores(scores) -> dict:
    if isinstance(scores, dict):
        return {str(key): _coerce_score(value) for key, value in scores.items()}
    if isinstance(scores, list):
        return {str(idx + 1): _coerce_score(score) for idx, score in enumerate(scores)}
    return {}


async def ingest_game_state(db: AsyncSession, data: dict, ip: str) -> None:
    machine_name = data.get("machine_name")
    machine_uid = data.get("machine_id") or data.get("machine_id_b64")
    reported_ip = (
        data.get("ip")
        or data.get("ip_address")
        or data.get("machine_ip")
        or ip
    )
    seconds_elapsed = int((data.get("gameTimeMs") or 0) / 1000)
    ball = int(data.get("ball_in_play") or 0)
    player_up = int(data.get("player_up") or 1)
    game_active = data.get("game_active", True)
    lock = _machine_lock(machine_uid or reported_ip)
    async with lock:
        machine = await _get_or_create_machine_by_uid(
            db, reported_ip, machine_uid, machine_name=machine_name
        )
        if not machine:
            return

        if game_active:
            game = await _ensure_active_game(db, machine)
        else:
            await _deactivate_active_game(db, machine)
            await db.commit()
            return

        game_state = models.GameState(
            game_id=game.id,
            seconds_elapsed=seconds_elapsed,
            ball=ball,
            player_up=player_up,
            scores=_normalize_scores(data.get("scores", {})),
        )
        db.add(game_state)
        await db.commit()
        logger.info(
            f"Saved game state for machine {machine.ip_address} on game {game.id}"
        )


async def _handle_discovery_message(message: DiscoveryMessage, ip: str) -> None:
    name = message.name.decode("utf-8", "ignore") if message.name else None
    peers: list[tuple[str, str]] = []
    if message.peers is not None:
        peers = [
            (_ip_bytes_to_str(peer_ip), peer_name.decode("utf-8", "ignore"))
            for peer_ip, peer_name in message.peers
        ]

    async with AsyncSessionLocal() as db:
        await ingest_discovery(db, ip, name=name, peers=peers)


async def _handle_game_state_message(data: dict, ip: str) -> None:
    async with AsyncSessionLocal() as db:
        await ingest_game_state(db, data, ip)


class UDPHandler(Protocol):
    async def handle_discovery(self, name: str | None, ip: str, peers: Iterable[tuple[str, str]]):
        ...

    async def handle_game_state(self, data: dict, ip: str):
        ...


class DbIngestHandler:
    async def handle_discovery(
        self, name: str | None, ip: str, peers: Iterable[tuple[str, str]]
    ):
        async with AsyncSessionLocal() as db:
            await ingest_discovery(db, ip, name=name, peers=peers)

    async def handle_game_state(self, data: dict, ip: str):
        async with AsyncSessionLocal() as db:
            await ingest_game_state(db, data, ip)


class DiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, handler: UDPHandler, port: int = DISCOVERY_PORT):
        self.port = port
        self._handler = handler

    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"UDP Listener started on {self.port}")

    def datagram_received(self, data, addr):
        logger.info(f"Received UDP discovery packet from {addr}")
        asyncio.create_task(self.process_message(data, addr))

    async def process_message(self, payload: bytes, addr):
        try:
            msg = DiscoveryMessage.decode(payload)
            if msg:
                name = msg.name.decode("utf-8", "ignore") if msg.name else None
                peers = []
                if msg.peers is not None:
                    peers = [
                        (_ip_bytes_to_str(peer_ip), peer_name.decode("utf-8", "ignore"))
                        for peer_ip, peer_name in msg.peers
                    ]
                await self._handler.handle_discovery(name, addr[0], peers)
            else:
                logger.debug("Ignored non-discovery packet on discovery port from %s", addr)
        except Exception as exc:  # pragma: no cover - safeguard
            logger.error(f"Error processing discovery UDP message: {exc}")


class GameStateProtocol(asyncio.DatagramProtocol):
    def __init__(self, handler: UDPHandler, port: int = GAME_STATE_PORT):
        self.port = port
        self._handler = handler

    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"UDP Listener started on {self.port}")

    def datagram_received(self, data, addr):
        logger.info(f"Received UDP game-state packet from {addr}")
        asyncio.create_task(self.process_message(data, addr))

    async def process_message(self, payload: bytes, addr):
        try:
            try:
                message = payload.decode()
                data = json.loads(message)
            except (UnicodeDecodeError, json.JSONDecodeError):
                logger.error(f"Failed to decode game state message from {addr}")
                return

            await self._handler.handle_game_state(data, addr[0])
        except Exception as exc:  # pragma: no cover - safeguard
            logger.error(f"Error processing game state UDP message: {exc}")


class UDPProtocol(asyncio.DatagramProtocol):
    """Backward-compatible protocol that delegates based on port."""

    def __init__(self, handler: UDPHandler | None = None, port: int = DISCOVERY_PORT):
        self.port = port
        ingest_handler = handler or DbIngestHandler()
        self._discovery_delegate = DiscoveryProtocol(ingest_handler, port)
        self._game_state_delegate = GameStateProtocol(ingest_handler, GAME_STATE_PORT)

    def connection_made(self, transport):
        self._discovery_delegate.connection_made(transport)
        self._game_state_delegate.connection_made(transport)

    def datagram_received(self, data, addr):
        delegate = (
            self._game_state_delegate if addr[1] == GAME_STATE_PORT else self._discovery_delegate
        )
        delegate.datagram_received(data, addr)

    async def process_message(self, payload: bytes, addr):
        delegate = (
            self._game_state_delegate if addr[1] == GAME_STATE_PORT else self._discovery_delegate
        )
        await delegate.process_message(payload, addr)


async def start_udp_server(
    host: str = "0.0.0.0",
    port: int = DISCOVERY_PORT,
    protocol_factory=None,
):
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        protocol_factory or (lambda: DiscoveryProtocol(DbIngestHandler(), port)),
        local_addr=(host, port),
    )
    return transport, protocol


async def start_udp_servers(host: str = "0.0.0.0", handler: UDPHandler | None = None):
    ingest_handler = handler or DbIngestHandler()
    discovery = await start_udp_server(
        host=host, port=DISCOVERY_PORT, protocol_factory=lambda: DiscoveryProtocol(ingest_handler, DISCOVERY_PORT)
    )
    game_state = await start_udp_server(
        host=host,
        port=GAME_STATE_PORT,
        protocol_factory=lambda: GameStateProtocol(ingest_handler, GAME_STATE_PORT),
    )
    return [discovery[0], game_state[0]]
