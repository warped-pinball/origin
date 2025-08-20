import os
import uuid
import string
import secrets
import json
from base64 import b64decode, b64encode
from functools import lru_cache
import logging

from fastapi import FastAPI, WebSocket, Depends
from cryptography.hazmat.primitives.asymmetric import x25519, padding
from cryptography.hazmat.primitives import hashes, serialization
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .database import init_db, get_db
from . import models

# Initialize database for WebSocket service
init_db()

app = FastAPI(title="Origin WS")


@lru_cache()
def get_signing_key():
    pem = os.environ.get("RSA_PRIVATE_KEY")
    if not pem:
        raise RuntimeError("RSA_PRIVATE_KEY not configured")
    return serialization.load_pem_private_key(pem.encode(), password=None)


def generate_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@app.websocket("/ws/setup")
async def ws_setup(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        payload = await websocket.receive_text()

        logger.info(f"Received setup payload: {payload}")

        parts = payload.split("|")
        # in the case of setup we do not care about the challenge, machine id or hmac
        payload = json.loads(parts[0])

        client_key_b64 = payload["client_key"]
        client_game_title = payload.get("game_title", "Unknown Game")
        client_public_bytes = b64decode(client_key_b64)
        client_public_key = x25519.X25519PublicKey.from_public_bytes(client_public_bytes)
    except Exception:
        await websocket.close()
        return

    server_private_key = x25519.X25519PrivateKey.generate()
    server_public_key = server_private_key.public_key()
    shared_secret = server_private_key.exchange(client_public_key)
    machine_id = str(uuid.uuid4())
    claim_code = generate_code()

    signing_key = get_signing_key()

    db_claim = models.MachineClaim(
        machine_id=machine_id,
        claim_code=claim_code,
        shared_secret=b64encode(shared_secret).decode(),
        client_game_title=client_game_title,
        claimed=False,
    )
    db.add(db_claim)
    db.commit()

    host = os.environ.get("PUBLIC_HOST_URL", "")
    claim_url = f"{host}/claim?code={claim_code}"

    msg = json.dumps(
        {
            "server_key": b64encode(
                server_public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                        format=serialization.PublicFormat.Raw,
                    )
                ).decode(),
            "claim_code": claim_code,
            "claim_url": claim_url,
            "machine_id": machine_id,
        },
        separators=(",", ":"),
    )
    msg_signature = signing_key.sign(msg.encode(), padding.PKCS1v15(), hashes.SHA256())
    msg += "|" + msg_signature.hex()

    logger.info("Message signed:", msg.encode())
    logger.info("Message signature:", msg_signature)

    logger.info(f"Sending setup response message: {msg}")
    await websocket.send_text(msg)
    await websocket.close()
