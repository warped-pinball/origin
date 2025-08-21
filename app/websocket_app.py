import os
import uuid
import string
import secrets
import json
import logging
import asyncio
from base64 import b64decode, b64encode
from functools import lru_cache
from typing import Dict, Any, Optional, Tuple

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from cryptography.hazmat.primitives.asymmetric import x25519, padding
from cryptography.hazmat.primitives import hashes, serialization
from sqlalchemy.orm import Session

from .database import init_db, get_db
from . import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database for WebSocket service
init_db()

app = FastAPI(title="Origin WS")


# ---------------------- Signing key ----------------------
@lru_cache()
def get_signing_key():
    pem = os.environ.get("RSA_PRIVATE_KEY")
    if not pem:
        raise RuntimeError("RSA_PRIVATE_KEY not configured")
    return serialization.load_pem_private_key(pem.encode(), password=None)


# ---------------------- Utilities ----------------------
def generate_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def parse_client_message(raw_text: str) -> Tuple[Dict[str, Any], Optional[str], Optional[str], Optional[str]]:
    """
    Split the client message on '|' into:
      - JSON payload (required)
      - client_id (optional)
      - challenge (optional)
      - hmac (optional)
    """
    parts = raw_text.split("|")
    if not parts:
        raise ValueError("Empty message")
    try:
        payload = json.loads(parts[0])
    except Exception as e:
        raise ValueError(f"Invalid JSON payload: {e}")
    client_id = parts[1] if len(parts) > 1 else None
    challenge = parts[2] if len(parts) > 2 else None
    hmac_value = parts[3] if len(parts) > 3 else None
    return payload, client_id, challenge, hmac_value


async def default_authenticator(payload: Dict[str, Any], client_id: Optional[str], challenge: Optional[str], hmac_value: Optional[str], db: Session) -> bool:
    """
    Allow setup handshake without enforcing HMAC/challenge.
    Add your auth logic here for other endpoints.
    """
    return True


def sign_json(obj: Dict[str, Any]) -> str:
    """
    Produce compact JSON and append a base64 RSA (PKCS1v15/SHA-256) signature.
    Returns "<json>|<base64_signature>".
    """
    response_json = json.dumps(obj, separators=(",", ":"))
    signing_key = get_signing_key()
    signature = signing_key.sign(response_json.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    signature_b64 = b64encode(signature).decode("ascii")
    return response_json + "|" + signature_b64


# ---------------------- Connection manager ----------------------
class ConnectionInfo:
    __slots__ = ("websocket", "machine_uuid_hex", "shared_secret")

    def __init__(self, websocket: WebSocket, machine_uuid_hex: str, shared_secret: bytes):
        self.websocket = websocket
        self.machine_uuid_hex = machine_uuid_hex
        self.shared_secret = shared_secret


class ConnectionManager:
    """
    Tracks many simultaneous connections, keyed by machine_uuid_hex.
    Provides send helpers and periodic heartbeats to detect dead sockets.
    """
    def __init__(self, heartbeat_interval_sec: int = 30):
        self._conns: Dict[str, ConnectionInfo] = {}
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
                await self.send_json(k, {"type": "ping"})
            except Exception as e:
                logger.info("Heartbeat failed for %s: %s. Evicting.", k, e)
                await self.disconnect(k)

    async def register(self, machine_uuid_hex: str, info: ConnectionInfo):
        async with self._lock:
            # Replace any existing connection for the same machine
            old = self._conns.get(machine_uuid_hex)
            self._conns[machine_uuid_hex] = info
        if old is not None:
            try:
                await old.websocket.close()
            except Exception:
                pass
        logger.info("Registered connection for machine=%s (total=%d)", machine_uuid_hex, await self.count())

    async def disconnect(self, machine_uuid_hex: str):
        async with self._lock:
            info = self._conns.pop(machine_uuid_hex, None)
        if info is not None:
            try:
                await info.websocket.close()
            except Exception:
                pass
            logger.info("Disconnected machine=%s (total=%d)", machine_uuid_hex, await self.count())

    async def count(self) -> int:
        async with self._lock:
            return len(self._conns)

    async def send_text(self, machine_uuid_hex: str, text: str):
        async with self._lock:
            info = self._conns.get(machine_uuid_hex)
        if info is None:
            raise RuntimeError("No active connection for machine {}".format(machine_uuid_hex))
        await info.websocket.send_text(text)

    async def send_json(self, machine_uuid_hex: str, obj: Dict[str, Any], sign: bool = True):
        if sign:
            await self.send_text(machine_uuid_hex, sign_json(obj))
        else:
            await self.send_text(machine_uuid_hex, json.dumps(obj, separators=(",", ":")))

    async def broadcast_json(self, obj: Dict[str, Any], sign: bool = True):
        async with self._lock:
            keys = list(self._conns.keys())
        for k in keys:
            try:
                await self.send_json(k, obj, sign=sign)
            except Exception as e:
                logger.info("Broadcast to %s failed: %s", k, e)
                await self.disconnect(k)


manager = ConnectionManager(heartbeat_interval_sec=30)


# ---------------------- Handshake decorator (persistent) ----------------------
def ws_persistent_handshake(authenticator=default_authenticator):
    """
    Decorator that:
      1) Accepts the socket and reads the initial text frame.
      2) Parses payload + optional auth parts.
      3) Calls the handler to perform key exchange and return:
            (response_obj: dict, machine_uuid_hex: str, shared_secret: bytes)
      4) Signs and sends the response (JSON + base64(signature)).
      5) Registers the connection with the ConnectionManager.
      6) Starts heartbeats (once).
      7) Enters a simple receive loop until the socket drops.
    The actual per-message logic can be expanded inside the loop.
    """
    def decorator(handler):
        async def endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
            await websocket.accept()
            try:
                raw_text = await websocket.receive_text()
                logger.info("Handshake received: %s", raw_text)

                payload, client_id, challenge, hmac_value = parse_client_message(raw_text)
                ok = await authenticator(payload, client_id, challenge, hmac_value, db)
                if not ok:
                    await websocket.close()
                    return

                response_obj, machine_uuid_hex, shared_secret = await handler(
                    payload=payload, db=db
                )

                # Send signed handshake response
                await websocket.send_text(sign_json(response_obj))

                # Register connection and begin heartbeats
                await manager.register(machine_uuid_hex, ConnectionInfo(websocket, machine_uuid_hex, shared_secret))
                await manager.start_heartbeats()

                # Persistent receive loop
                while True:
                    try:
                        msg = await websocket.receive_text()
                    except WebSocketDisconnect:
                        logger.info("WebSocketDisconnect for machine=%s", machine_uuid_hex)
                        break
                    except Exception as e:
                        logger.info("Receive error for machine=%s: %s", machine_uuid_hex, e)
                        break

                    # Basic routing: expect either "<json>|<base64(signature)>" (signed by server only if we push)
                    # or plain JSON. For now, we just parse JSON and log. Extend as needed.
                    try:
                        # If boards send your legacy pipe+HMAC form, detect and handle here.
                        if "|" in msg:
                            # If later you make clients sign messages, you can split here and verify.
                            json_part = msg.split("|", 1)[0]
                        else:
                            json_part = msg
                        obj = json.loads(json_part)
                        logger.info("Received from %s: %s", machine_uuid_hex, obj)
                        # TODO: act on commands from device if needed.
                    except Exception:
                        logger.info("Non-JSON message from %s: %s", machine_uuid_hex, msg)

            except Exception as e:
                logger.exception("Handshake/connection error: %s", e)
            finally:
                # Ensure deregistration
                # We need machine id to deregister; if handshake failed before it's known, no-op.
                try:
                    await manager.disconnect(machine_uuid_hex)  # type: ignore
                except Exception:
                    pass

        # Important: do NOT use @wraps here to avoid signature confusion with FastAPI
        endpoint.__name__ = getattr(handler, "__name__", "ws_endpoint")
        return endpoint
    return decorator


# ---------------------- Setup handler (key exchange) ----------------------
@app.websocket("/ws/setup")
@ws_persistent_handshake(authenticator=default_authenticator)
async def ws_setup_handler(*, payload: Dict[str, Any], db: Session) -> Tuple[Dict[str, Any], str, bytes]:
    """
    Performs X25519 key exchange and returns:
       - response_obj (dict): includes server_key, claim_code, claim_url, machine_id (base64 UUID bytes)
       - machine_uuid_hex (str): registry key for manager
       - shared_secret (bytes): raw shared secret (for future use)
    """
    # Parse client key
    try:
        client_key_b64 = payload["client_key"]
        client_game_title = payload.get("game_title", "Unknown Game")
        client_public_bytes = b64decode(client_key_b64)
        client_public_key = x25519.X25519PublicKey.from_public_bytes(client_public_bytes)
    except Exception as e:
        raise ValueError(f"Invalid client payload: {e}")

    # Generate server key pair and shared secret
    server_private_key = x25519.X25519PrivateKey.generate()
    server_public_key = server_private_key.public_key()
    shared_secret = server_private_key.exchange(client_public_key)

    # Machine ID as 16 raw bytes, base64-encoded in response; hex persisted internally
    machine_uuid = uuid.uuid4()
    machine_uuid_hex = machine_uuid.hex
    machine_id_b64 = b64encode(machine_uuid.bytes).decode("ascii")

    claim_code = generate_code()

    # Persist claim
    db_claim = models.MachineClaim(
        machine_id=machine_uuid_hex,
        claim_code=claim_code,
        shared_secret=b64encode(shared_secret).decode("ascii"),
        client_game_title=client_game_title,
        claimed=False,
    )
    db.add(db_claim)
    db.commit()

    host = os.environ.get("PUBLIC_HOST_URL", "")
    claim_url = f"{host}/claim?code={claim_code}"

    logger.info("Shared secret (hex) for %s: %s", machine_uuid_hex, shared_secret.hex())

    response_obj = {
        "server_key": b64encode(
            server_public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        ).decode("ascii"),
        "claim_code": claim_code,
        "claim_url": claim_url,
        "machine_id": machine_id_b64,
    }

    # Return tuple as specified by decorator contract
    return response_obj, machine_uuid_hex, shared_secret


#TODO break out a generic "handle request" function which will sign all messages
#TODO include "next challenge" in all responses
#TODO base64 encode everything we can
#TODO add any commands we want to send back 
#TODO keep websocket open?
#TODO store things as base64 not hex (like machine id)