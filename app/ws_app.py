from functools import cache
import hashlib
import hmac
import secrets
import string
from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketState
from fastapi import Depends
from typing import Dict, Any, Union
import asyncio
import json
import logging
from sqlalchemy.orm import Session
from base64 import b64decode, b64encode
import uuid
from datetime import datetime, timedelta, timezone
import os
from cryptography.hazmat.primitives.asymmetric import x25519
from . import models
from .database import init_db, get_db
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Connection:
    def __init__(self, machine_id: str, websocket: WebSocket):
        self.machine_id = machine_id
        self.websocket = websocket
        self.last_active = datetime.now()
        self._shared_secret = None

    @property
    def shared_secret(self):
        if self._shared_secret is None:
            # get the shared secret from the db
            self._shared_secret = get_shared_secret(self.machine_id)
        return self._shared_secret

    @shared_secret.setter
    def shared_secret(self, value):
        self._shared_secret = value
        # TODO write to DB

    def send_text(self, message: str) -> None:
        self.last_active = datetime.now()
        return self.websocket.send_text(message)

    def receive_text(self) -> str:
        msg = self.websocket.receive_text()
        if msg:
            self.last_active = datetime.now()
        return msg

    def close(self) -> None:
        return self.websocket.close()


class ConnectionManager:
    def __init__(self) -> None:
        self._clients: Dict[str, Connection] = {}
        self._lock = asyncio.Lock()

    async def add(self, machine_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients[machine_id] = Connection(machine_id, websocket)

    async def remove(self, machine_id: str) -> None:
        async with self._lock:
            self._clients.pop(machine_id, None)

    async def send_to(self, machine_id: str, message: Any) -> None:
        async with self._lock:
            ws = self._clients.get(machine_id)
        if not ws or ws.application_state != WebSocketState.CONNECTED:
            raise RuntimeError("WebSocket is not connected.")
        await ws.send_text(message if isinstance(message, str) else json.dumps(message))


connection_manager = ConnectionManager()
app = FastAPI(title="Origin WS")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            route, message = data.split("|", 1)
            if route in routes:
                try:
                    await routes[route](db, websocket, message)
                except Exception as e:
                    logger.warning(f"Error handling route {route}: {e}")

    except Exception as e:
        logger.warning(f"WebSocket error: {e}")


def authenticate_hmac(handler):
    def wrapper(db: Session, websocket: WebSocket, message: str):
        payload, hmac_value = message.rsplit("|", 1)
        data, machine_id, challenge = payload.rsplit("|", 3)

        if not data or not machine_id or not challenge:
            raise ValueError("Invalid payload format")

        result = (
            db.query(models.Machine, models.MachineChallenge)
            .join(models.MachineChallenge, models.Machine.id == models.MachineChallenge.machine_id)
            .filter(models.Machine.id == machine_id)
            .filter(models.MachineChallenge.challenge == challenge)
            .first()
        )
        if not result:
            raise ValueError("Invalid machine ID or challenge")
        machine, ch = result
        
        issued_at = ch.issued_at
        if issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=timezone.utc)
        if issued_at < datetime.now(timezone.utc) - timedelta(days=1):
            # remove the challenge from the db
            db.delete(ch)
            db.commit()
            send_new_challenges(db, websocket, machine_id, n=10)
            raise ValueError("Challenge expired")

        
        secret = b64decode(machine.shared_secret)
        
        
        expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, hmac_value):
            raise ValueError("Invalid HMAC")

        db.delete(ch)
        db.commit()

        try:
            handler(db, websocket, data)
        except Exception as e:
            logger.warning(f"Error handling message: {e}")

        # create new challenge
        new_challenge = models.MachineChallenge(
            machine_id=machine.id,
            challenge=secrets.token_urlsafe(32),
            issued_at=datetime.now(timezone.utc),
        )
        db.add(new_challenge)
        db.commit()

        try:
            send_message(websocket, "challenge", new_challenge.challenge)
        except Exception as e:
            logger.warning(f"Error handling message: {e}")

    return wrapper


@cache()
def get_signing_key():
    pem = os.environ.get("RSA_PRIVATE_KEY")
    if not pem:
        raise RuntimeError("RSA_PRIVATE_KEY not configured")
    return serialization.load_pem_private_key(pem.encode(), password=None)


def send_message(websocket: WebSocket, route: str, message: Union[str, dict]):
    # Convert message to JSON string if it's not already a string
    if not isinstance(message, str):
        try:
            message = json.dumps(message, separators=(",", ":"))
        except (TypeError, ValueError):
            logger.warning(f"Failed to serialize message: {message}")
            return

    # Sign if requested
    signing_key = get_signing_key()
    signature = signing_key.sign(
        message.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    signature_b64 = b64encode(signature).decode("ascii")
    message += "|" + signature_b64

    asyncio.create_task(websocket.send_text(message))

def send_new_challenges(db: Session, websocket: WebSocket, machine_id: str, n: int = 10):

    # get the machine from the db
    machine = db.query(models.Machine).filter_by(id=machine_id).first()
    if not machine:
        logger.warning(f"Machine not found: {machine_id}")
        return

    new_challenges = []
    for _ in range(n):
        new_challenge = models.MachineChallenge(
            machine_id=machine.id,
            challenge=secrets.token_urlsafe(32),
            issued_at=datetime.now(timezone.utc),
        )
        db.add(new_challenge)
        db.commit()
        new_challenges.append(new_challenge)

    try:
        send_message(websocket, "challenges", [challenge.challenge for challenge in new_challenges])
    except Exception as e:
        logger.warning(f"Error handling message: {e}")

def handle_handshake(websocket, message):
    data = json.loads(message)

    try:
        client_public_bytes = b64decode(data.get("client_key"))
        client_public_key = x25519.X25519PublicKey.from_public_bytes(
            client_public_bytes
        )
        client_game_title = data.get("game_title", "Unknown Game")
    except Exception as e:
        logger.warning(f"Failed to process handshake message: {e}")
        return

    server_private_key = x25519.X25519PrivateKey.generate()
    server_public_key = server_private_key.public_key()

    shared_secret = server_private_key.exchange(client_public_key)
    machine_uuid = uuid.uuid4()
    machine_uuid_hex = machine_uuid.hex
    machine_id_b64 = b64encode(machine_uuid.bytes).decode("ascii")

    alphabet = string.ascii_uppercase + string.digits
    claim_code = "".join(secrets.choice(alphabet) for _ in range(8))

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
                format=serialization.PublicFormat.Raw,
            )
        ).decode("ascii"),
        "claim_code": claim_code,
        "claim_url": claim_url,
        "machine_id": machine_id_b64,
    }

    send_message(websocket, "handshake", response_obj, signed=True)

def handle_request_challenges(db: Session, websocket: WebSocket, message: str):
    # generate n new challenges
    data, machine_id = message.rsplit("|", 1)
    data = json.loads(data)
    n = data.get("num", 10)

    send_new_challenges(db, websocket, machine_id, n)

def send_new_challenges(db: Session, websocket: WebSocket, machine_id: str, n: int = 10):

    # get the machine from the db
    machine = db.query(models.Machine).filter_by(id=machine_id).first()
    if not machine:
        logger.warning(f"Machine not found: {machine_id}")
        return

    new_challenges = []
    for _ in range(n):
        new_challenge = models.MachineChallenge(
            machine_id=machine.id,
            challenge=secrets.token_urlsafe(32),
            issued_at=datetime.now(timezone.utc),
        )
        db.add(new_challenge)
        db.commit()
        new_challenges.append(new_challenge)

    try:
        send_message(websocket, "challenges", [challenge.challenge for challenge in new_challenges])
    except Exception as e:
        logger.warning(f"Error handling message: {e}")

def send_claimed(db: Session, websocket: WebSocket, machine_id: str):
    # get the user for the machine from the db
    user = db.query(models.User).filter_by(machine_id=machine_id).first()
    if not user:
        logger.warning(f"User not found for machine: {machine_id}")
        return

    machineClaim = db.query(models.MachineClaim).filter_by(machine_id=machine_id).first()
    if not machineClaim:
        logger.warning(f"Machine claim not found: {machine_id}")
        return

    try:
        send_message(websocket, "claimed", {"user_id": user.id})
    except Exception as e:
        logger.warning(f"Error handling message: {e}")

    db.delete(machineClaim)
    db.commit()

routes = {"handshake": handle_handshake}