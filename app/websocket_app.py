import os
import uuid
import json
import logging
from base64 import b64decode, b64encode
from typing import Dict, Any, Tuple

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
from sqlalchemy.orm import Session

from .database import init_db, get_db
from . import models
from .ws import (
    ConnectionManager,
    WSConnection,
    parse_client_message,
    sign_json,
    ws_router,
    default_authenticator,
    generate_code,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database for WebSocket service
init_db()

app = FastAPI(title="Origin WS")

manager = ConnectionManager(heartbeat_interval_sec=30)


def ws_persistent_handshake(*, authenticator=default_authenticator, require_auth: bool = True):
    def decorator(handler):
        async def endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
            await websocket.accept()
            machine_uuid_hex = ""
            try:
                raw_text = await websocket.receive_text()
                logger.info("Handshake received: %s", raw_text)
                payload, client_id, challenge, hmac_value = parse_client_message(raw_text)
                if require_auth:
                    ok = await authenticator(payload, client_id, challenge, hmac_value, db)
                    if not ok:
                        await websocket.close()
                        return

                response_obj, machine_uuid_hex, shared_secret = await handler(payload=payload, db=db)
                await websocket.send_text(sign_json(response_obj))

                conn = WSConnection(websocket, machine_uuid_hex, shared_secret)
                await manager.register(machine_uuid_hex, conn)
                await manager.start_heartbeats()

                while True:
                    try:
                        payload, client_id, challenge, hmac_value = await conn.receive()
                    except WebSocketDisconnect:
                        logger.info("WebSocketDisconnect for machine=%s", machine_uuid_hex)
                        break
                    except Exception as e:
                        logger.info("Receive error for machine=%s: %s", machine_uuid_hex, e)
                        break

                    await ws_router.dispatch(conn, payload, client_id, challenge, hmac_value, db)
            except Exception as e:
                logger.exception("Handshake/connection error: %s", e)
            finally:
                try:
                    await manager.disconnect(machine_uuid_hex)
                except Exception:
                    pass

        endpoint.__name__ = getattr(handler, "__name__", "ws_endpoint")
        return endpoint

    return decorator


@app.websocket("/ws/setup")
@ws_persistent_handshake(require_auth=False)
async def ws_setup_handler(*, payload: Dict[str, Any], db: Session) -> Tuple[Dict[str, Any], str, bytes]:
    try:
        client_key_b64 = payload["client_key"]
        client_game_title = payload.get("game_title", "Unknown Game")
        client_public_bytes = b64decode(client_key_b64)
        client_public_key = x25519.X25519PublicKey.from_public_bytes(client_public_bytes)
    except Exception as e:
        raise ValueError(f"Invalid client payload: {e}")

    server_private_key = x25519.X25519PrivateKey.generate()
    server_public_key = server_private_key.public_key()
    shared_secret = server_private_key.exchange(client_public_key)

    machine_uuid = uuid.uuid4()
    machine_uuid_hex = machine_uuid.hex
    machine_id_b64 = b64encode(machine_uuid.bytes).decode("ascii")

    claim_code = generate_code()

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

    return response_obj, machine_uuid_hex, shared_secret
