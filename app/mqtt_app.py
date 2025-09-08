"""MQTT message handler for Origin."""

from __future__ import annotations

import json
import logging
import os
import secrets
import string
import uuid
from base64 import b64decode, b64encode
from datetime import datetime, timezone
from typing import Union

from paho.mqtt import client as mqtt_client
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, x25519


logger = logging.getLogger(__name__)

MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "origin")


def get_signing_key():
    pem = os.environ.get("RSA_PRIVATE_KEY")
    if not pem:
        raise RuntimeError("RSA_PRIVATE_KEY not configured")
    return serialization.load_pem_private_key(pem.encode(), password=None)


def _topic(machine_id: str | None = None) -> str:
    return f"{MQTT_TOPIC_PREFIX}/{machine_id}" if machine_id else MQTT_TOPIC_PREFIX


def send_message(
    client: mqtt_client.Client,
    route: str,
    message: Union[str, dict],
    *,
    machine_id: str | None = None,
    signed: bool = False,
) -> None:
    """Publish a message to the broker."""

    if not isinstance(message, str):
        try:
            message = json.dumps(message, separators=(",", ":"))
        except (TypeError, ValueError):
            logger.warning("Failed to serialize message: %s", message)
            return

    if signed:
        signing_key = get_signing_key()
        signature = signing_key.sign(
            message.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        message += "|" + b64encode(signature).decode("ascii")

    payload = f"{route}|{message}"
    client.publish(_topic(machine_id), payload)


def handle_handshake(db: Session, client: mqtt_client.Client, message: str) -> None:
    data = json.loads(message)

    try:
        client_public_bytes = b64decode(data.get("client_key"))
        client_public_key = x25519.X25519PublicKey.from_public_bytes(
            client_public_bytes
        )
        client_game_title = data.get("game_title", "Unknown Game")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to process handshake message: %s", exc)
        return

    server_private_key = x25519.X25519PrivateKey.generate()
    server_public_key = server_private_key.public_key()

    shared_secret = server_private_key.exchange(client_public_key)
    shared_secret_b64 = b64encode(shared_secret).decode("ascii")
    machine_uuid = uuid.uuid4()
    machine_uuid_hex = machine_uuid.hex
    machine_id_b64 = b64encode(machine_uuid.bytes).decode("ascii")

    db_machine = models.Machine(
        id=machine_uuid_hex,
        game_title=client_game_title,
        shared_secret=shared_secret_b64,
    )
    db.add(db_machine)

    alphabet = string.ascii_uppercase + string.digits
    claim_code = "".join(secrets.choice(alphabet) for _ in range(8))
    db_claim = models.MachineClaim(machine_id=machine_uuid_hex, claim_code=claim_code)
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

    send_message(
        client,
        "handshake",
        response_obj,
        machine_id=machine_uuid_hex,
        signed=True,
    )


def send_new_challenges(
    db: Session, client: mqtt_client.Client, machine_id: str, n: int = 10
) -> None:
    machine = db.query(models.Machine).filter_by(id=machine_id).first()
    if not machine:
        logger.warning("Machine not found: %s", machine_id)
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
        send_message(
            client,
            "challenges",
            [challenge.challenge for challenge in new_challenges],
            machine_id=machine_id,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Error handling message: %s", exc)


def send_claimed(db: Session, client: mqtt_client.Client, machine_id: str) -> None:
    user = db.query(models.User).filter_by(machine_id=machine_id).first()
    if not user:
        logger.warning("User not found for machine: %s", machine_id)
        return

    machine_claim = (
        db.query(models.MachineClaim).filter_by(machine_id=machine_id).first()
    )
    if not machine_claim:
        logger.warning("Machine claim not found: %s", machine_id)
        return

    try:
        send_message(client, "claimed", {"user_id": user.id}, machine_id=machine_id)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Error handling message: %s", exc)

    db.delete(machine_claim)
    db.commit()


def handle_request_challenges(
    db: Session, client: mqtt_client.Client, message: str
) -> None:
    data, machine_id = message.rsplit("|", 1)
    data = json.loads(data)
    n = data.get("num", 10)
    send_new_challenges(db, client, machine_id, n)


routes = {
    "handshake": handle_handshake,
    "request_challenges": handle_request_challenges,
}


def _with_db(handler, client: mqtt_client.Client, message: str) -> None:
    db_gen = get_db()
    db = next(db_gen)
    try:
        handler(db, client, message)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


def on_message(client, userdata, msg) -> None:
    try:
        data = msg.payload.decode()
        route, message = data.split("|", 1)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Invalid message: %s", exc)
        return

    handler = routes.get(route)
    if handler:
        _with_db(handler, client, message)


def start() -> None:
    logging.basicConfig(level=logging.INFO)
    client = mqtt_client.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe(f"{MQTT_TOPIC_PREFIX}/#")
    client.loop_forever()


if __name__ == "__main__":
    start()

