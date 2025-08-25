import os
import json
import hmac
import hashlib
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from base64 import b64encode, b64decode
from functools import lru_cache
from typing import Dict, Any, Optional, Tuple, Callable

from fastapi import WebSocket
from sqlalchemy.orm import Session

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from . import models

logger = logging.getLogger(__name__)


@lru_cache()
def get_signing_key():
    pem = os.environ.get("RSA_PRIVATE_KEY")
    if not pem:
        raise RuntimeError("RSA_PRIVATE_KEY not configured")
    return serialization.load_pem_private_key(pem.encode(), password=None)


def generate_code(length: int = 8) -> str:
    import string
    import secrets

    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def parse_client_message(
    raw_text: str,
) -> Tuple[str, Dict[str, Any], Optional[str], Optional[str], Optional[str]]:
    parts = raw_text.split("|")
    if len(parts) < 2:
        raise ValueError("Message missing route or payload")
    route = parts[0]
    try:
        payload = json.loads(parts[1])
    except Exception as e:
        raise ValueError(f"Invalid JSON payload: {e}")
    client_id = parts[2] if len(parts) > 2 else None
    challenge = parts[3] if len(parts) > 3 else None
    hmac_value = parts[4] if len(parts) > 4 else None
    return route, payload, client_id, challenge, hmac_value


def sign_message(route: str, obj: Dict[str, Any]) -> str:
    payload_json = json.dumps(obj, separators=(",", ":"))
    signing_key = get_signing_key()
    message = f"{route}|{payload_json}"
    signature = signing_key.sign(
        message.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    signature_b64 = b64encode(signature).decode("ascii")
    return message + "|" + signature_b64


class WSConnection:
    __slots__ = ("websocket", "machine_uuid_hex", "shared_secret")

    def __init__(
        self, websocket: WebSocket, machine_uuid_hex: str, shared_secret: bytes
    ):
        self.websocket = websocket
        self.machine_uuid_hex = machine_uuid_hex
        self.shared_secret = shared_secret

    async def receive(
        self,
    ) -> Tuple[str, Dict[str, Any], Optional[str], Optional[str], Optional[str]]:
        text = await self.websocket.receive_text()
        return parse_client_message(text)
    async def send_json(self, route: str, obj: Dict[str, Any]):
        await self.websocket.send_text(sign_message(route, obj))


class ConnectionManager:
    def __init__(self, heartbeat_interval_sec: int = 30):
        self._conns: Dict[str, WSConnection] = {}
        self._lock = asyncio.Lock()
        self._hb_interval = heartbeat_interval_sec
        self._hb_task: Optional[asyncio.Task] = None

    async def start_heartbeats(self):
        if self._hb_task is None:
            self._hb_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(self._hb_interval)
            await self._ping_all()

    async def _ping_all(self):
        async with self._lock:
            keys = list(self._conns.keys())
        for k in keys:
            try:
                await self.send_json(k, "ping", {})
            except Exception as e:
                logger.info("Heartbeat failed for %s: %s. Evicting.", k, e)
                await self.disconnect(k)

    async def register(self, machine_uuid_hex: str, conn: WSConnection):
        async with self._lock:
            old = self._conns.get(machine_uuid_hex)
            self._conns[machine_uuid_hex] = conn
        if old is not None:
            try:
                await old.websocket.close()
            except Exception:
                pass
        logger.info(
            "Registered connection for machine=%s (total=%d)",
            machine_uuid_hex,
            await self.count(),
        )

    async def disconnect(self, machine_uuid_hex: str):
        async with self._lock:
            conn = self._conns.pop(machine_uuid_hex, None)
        if conn is not None:
            try:
                await conn.websocket.close()
            except Exception:
                pass
            logger.info(
                "Disconnected machine=%s (total=%d)",
                machine_uuid_hex,
                await self.count(),
            )

    async def count(self) -> int:
        async with self._lock:
            return len(self._conns)

    async def send_json(self, machine_uuid_hex: str, route: str, obj: Dict[str, Any]):
        async with self._lock:
            conn = self._conns.get(machine_uuid_hex)
        if conn is None:
            raise RuntimeError(
                "No active connection for machine {}".format(machine_uuid_hex)
            )
        await conn.websocket.send_text(sign_message(route, obj))

    async def broadcast_json(self, route: str, obj: Dict[str, Any]):
        async with self._lock:
            keys = list(self._conns.keys())
        for k in keys:
            try:
                await self.send_json(k, route, obj)
            except Exception as e:
                logger.info("Broadcast to %s failed: %s", k, e)
                await self.disconnect(k)


async def default_authenticator(
    payload: Dict[str, Any],
    client_id: Optional[str],
    challenge: Optional[str],
    hmac_value: Optional[str],
    db: Session,
) -> bool:
    if not (client_id and challenge and hmac_value):
        return False

    ch = db.query(models.MachineChallenge).filter_by(challenge=challenge).first()
    if not ch or ch.used:
        return False
    if ch.machine_id != client_id:
        return False
    issued_at = ch.issued_at
    if issued_at.tzinfo is None:
        issued_at = issued_at.replace(tzinfo=timezone.utc)
    if issued_at < datetime.now(timezone.utc) - timedelta(hours=1):
        return False

    claim = db.query(models.MachineClaim).filter_by(machine_id=client_id).first()
    if not claim:
        return False
    secret = b64decode(claim.shared_secret)
    payload_json = json.dumps(payload, separators=(",", ":")).encode()
    msg = challenge.encode() + payload_json
    expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, hmac_value):
        return False

    ch.used = True
    db.add(ch)
    db.commit()
    return True


class MessageRouter:
    def __init__(self, authenticator: Callable = default_authenticator):
        self.authenticator = authenticator
        self._handlers: Dict[str, Tuple[Callable, bool]] = {}

    def handler(self, route: str, *, require_auth: bool = True):
        def decorator(func: Callable):
            self._handlers[route] = (func, require_auth)
            return func

        return decorator

    async def dispatch(
        self,
        connection: WSConnection,
        route: str,
        payload: Dict[str, Any],
        client_id: Optional[str],
        challenge: Optional[str],
        hmac_value: Optional[str],
        db: Session,
    ):
        entry = self._handlers.get(route)
        if not entry:
            logger.info("No handler for route %s", route)
            return
        handler, require_auth = entry
        if require_auth:
            ok = await self.authenticator(payload, client_id, challenge, hmac_value, db)
            if not ok:
                logger.info("Auth failed for route %s", route)
                return
        await handler(connection, payload, db)


ws_router = MessageRouter()
