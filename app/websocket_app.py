import os
import uuid
import string
import secrets
import json
import logging
from base64 import b64decode, b64encode
from functools import lru_cache, wraps
from typing import Callable, Awaitable, Dict, Any, Optional, Tuple

from fastapi import FastAPI, WebSocket, Depends
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


@lru_cache()
def get_signing_key():
    """
    Load an RSA private key from the environment variable RSA_PRIVATE_KEY (PEM).
    """
    pem = os.environ.get("RSA_PRIVATE_KEY")
    if not pem:
        raise RuntimeError("RSA_PRIVATE_KEY not configured")
    return serialization.load_pem_private_key(pem.encode(), password=None)


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

    Returns: (payload_dict, client_id, challenge, hmac)
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


async def default_authenticator(
    payload: Dict[str, Any],
    client_id: Optional[str],
    challenge: Optional[str],
    hmac_value: Optional[str],
    db: Session,
) -> bool:
    """
    Default authenticator that allows the setup flow without HMAC validation.
    Replace with real validation when you want to enforce HMAC + challenge.
    """
    # For /ws/setup, we intentionally skip validation. Return True to continue.
    return True


def ws_signed_endpoint(
    *,
    authenticator: Callable[[Dict[str, Any], Optional[str], Optional[str], Optional[str], Session], Awaitable[bool]]
):
    def decorator(handler: Callable[..., Awaitable[Dict[str, Any]]]):
        # DO NOT use @wraps(handler): it would copy the handler's signature and drop the Depends default
        async def wrapper(websocket: WebSocket, db: Session = Depends(get_db)):
            await websocket.accept()
            try:
                raw_text = await websocket.receive_text()
                logger.info("Received message: %s", raw_text)

                payload, client_id, challenge, hmac_value = parse_client_message(raw_text)

                ok = await authenticator(payload, client_id, challenge, hmac_value, db)
                if not ok:
                    await websocket.close()
                    return

                response_obj = await handler(
                    websocket=websocket,
                    db=db,
                    payload=payload,
                    client_id=client_id,
                    challenge=challenge,
                    hmac_value=hmac_value,
                )

                # Compact JSON and sign
                response_json = json.dumps(response_obj, separators=(",", ":"))
                signing_key = get_signing_key()
                signature = signing_key.sign(response_json.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
                signature_b64 = b64encode(signature).decode("ascii")

                await websocket.send_text(response_json + "|" + signature_b64)
            except Exception as e:
                logger.exception("WebSocket error: %s", e)
            finally:
                try:
                    await websocket.close()
                except Exception:
                    pass

        # optional: keep the original name for nicer logs, but DO NOT copy __signature__
        wrapper.__name__ = getattr(handler, "__name__", "ws_handler")
        return wrapper
    return decorator


@app.websocket("/ws/setup")
@ws_signed_endpoint()
async def ws_setup_handler(
    *,
    websocket: WebSocket,
    db: Session,
    payload: Dict[str, Any],
    client_id: Optional[str],
    challenge: Optional[str],
    hmac_value: Optional[str],
) -> Dict[str, Any]:
    """
    Performs X25519 key exchange and returns:
      - server_key: base64(X25519 public key bytes)
      - claim_code: 8-char code
      - claim_url: PUBLIC_HOST_URL + /claim?code=...
      - machine_id: base64(uuid bytes)  <-- CHANGED to base64
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

    # Machine ID as 16 raw bytes, base64-encoded (not the hex string)
    machine_uuid = uuid.uuid4()
    machine_id_b64 = b64encode(machine_uuid.bytes).decode("ascii")

    claim_code = generate_code()

    # Persist claim
    db_claim = models.MachineClaim(
        machine_id=machine_uuid.hex,             # store hex internally as before
        claim_code=claim_code,
        shared_secret=b64encode(shared_secret).decode("ascii"),
        client_game_title=client_game_title,
        claimed=False,
    )
    db.add(db_claim)
    db.commit()

    # Construct claim URL
    host = os.environ.get("PUBLIC_HOST_URL", "")
    claim_url = f"{host}/claim?code={claim_code}"

    # Helpful log lines
    logger.info("Shared secret (hex): %s", shared_secret.hex())
    logger.info("Machine UUID (hex): %s", machine_uuid.hex)

    # Build response object (unsigned here; decorator signs it)
    response = {
        "server_key": b64encode(
            server_public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        ).decode("ascii"),
        "claim_code": claim_code,
        "claim_url": claim_url,
        "machine_id": machine_id_b64,  # base64-encoded UUID bytes
    }
    return response

#TODO break out a generic "handle request" function which will sign all messages
#TODO include "next challenge" in all responses
#TODO base64 encode everything we can
#TODO add any commands we want to send back 
#TODO keep websocket open?
#TODO store things as base64 not hex (like machine id)