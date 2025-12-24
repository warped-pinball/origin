"""UDP utilities for the Ray forwarding service."""

import asyncio
import json
import logging
from collections.abc import Iterable
from typing import Protocol

logger = logging.getLogger(__name__)

# The Pico 2W boards broadcast discovery messages on this port
DISCOVERY_PORT = 37020
# Game state updates are broadcast separately on this port
GAME_STATE_PORT = 6809


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
        peers: Iterable[tuple[bytes, bytes]] | None = None,
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


class UDPHandler(Protocol):
    async def handle_discovery(self, name: str | None, ip: str, peers: Iterable[tuple[str, str]]):
        ...

    async def handle_game_state(self, data: dict, ip: str):
        ...


class DiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, handler: UDPHandler, port: int = DISCOVERY_PORT):
        self.port = port
        self._handler = handler
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        asyncio.create_task(self.process_message(data, addr))

    async def process_message(self, data: bytes, addr):
        try:
            message = DiscoveryMessage.decode(data)
            if not message:
                logger.warning("Invalid discovery message from %s", addr)
                return
            name = _normalize_machine_name(
                message.name.decode("utf-8", "ignore") if message.name else None
            )
            peers: list[tuple[str, str]] = []
            if message.peers is not None:
                peers = [
                    (_ip_bytes_to_str(peer_ip), peer_name.decode("utf-8", "ignore"))
                    for peer_ip, peer_name in message.peers
                ]
            await self._handler.handle_discovery(name, addr[0], peers)
        except Exception as exc:  # pragma: no cover - safeguard
            logger.error("Error processing discovery UDP message: %s", exc)


class GameStateProtocol(asyncio.DatagramProtocol):
    def __init__(self, handler: UDPHandler, port: int = GAME_STATE_PORT):
        self.port = port
        self._handler = handler
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        asyncio.create_task(self.process_message(data, addr))

    async def process_message(self, data: bytes, addr):
        try:
            payload = json.loads(data)
            await self._handler.handle_game_state(payload, addr[0])
        except json.JSONDecodeError:
            logger.warning("Malformed game state packet from %s", addr)
        except Exception as exc:  # pragma: no cover - safeguard
            logger.error("Error processing game state UDP message: %s", exc)


class UDPProtocol(asyncio.DatagramProtocol):
    """Backward-compatible protocol that delegates based on port."""

    def __init__(self, handler: UDPHandler, port: int = DISCOVERY_PORT):
        self.port = port
        self._handler = handler
        self._discovery_delegate = DiscoveryProtocol(handler, port)
        self._game_state_delegate = GameStateProtocol(handler, GAME_STATE_PORT)

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
        protocol_factory,  # type: ignore[arg-type]
        local_addr=(host, port),
    )
    return transport, protocol


async def start_udp_servers(host: str = "0.0.0.0", handler: UDPHandler | None = None):
    if handler is None:
        raise ValueError("UDP handler is required for the Ray service")

    discovery = await start_udp_server(
        host=host, port=DISCOVERY_PORT, protocol_factory=lambda: DiscoveryProtocol(handler, DISCOVERY_PORT)
    )
    game_state = await start_udp_server(
        host=host,
        port=GAME_STATE_PORT,
        protocol_factory=lambda: GameStateProtocol(handler, GAME_STATE_PORT),
    )
    return [discovery[0], game_state[0]]
