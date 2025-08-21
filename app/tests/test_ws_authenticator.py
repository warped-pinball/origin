import asyncio
import base64
import hmac
import hashlib
import json
from datetime import datetime, timedelta, timezone

from app import models
from app.ws import default_authenticator


def test_default_authenticator_valid(db_session):
    machine_id = "abcd1234"
    secret = b"supersecret"
    claim = models.MachineClaim(
        machine_id=machine_id,
        claim_code="CODE1",
        shared_secret=base64.b64encode(secret).decode(),
        client_game_title="Game",
        claimed=True,
    )
    challenge = models.MachineChallenge(
        challenge="chal1",
        machine_id=machine_id,
        issued_at=datetime.now(timezone.utc),
        used=False,
    )
    db_session.add_all([claim, challenge])
    db_session.commit()

    payload = {"action": "test"}
    msg = challenge.challenge.encode() + json.dumps(payload, separators=(",", ":")).encode()
    h = hmac.new(secret, msg, hashlib.sha256).hexdigest()

    assert asyncio.run(default_authenticator(payload, machine_id, challenge.challenge, h, db_session))


def test_default_authenticator_rejects_used(db_session):
    machine_id = "abcd5678"
    secret = b"supersecret"
    claim = models.MachineClaim(
        machine_id=machine_id,
        claim_code="CODE2",
        shared_secret=base64.b64encode(secret).decode(),
        client_game_title="Game",
        claimed=True,
    )
    challenge = models.MachineChallenge(
        challenge="chal2",
        machine_id=machine_id,
        issued_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        used=True,
    )
    db_session.add_all([claim, challenge])
    db_session.commit()

    payload = {"action": "test"}
    msg = challenge.challenge.encode() + json.dumps(payload, separators=(",", ":")).encode()
    h = hmac.new(secret, msg, hashlib.sha256).hexdigest()

    assert not asyncio.run(default_authenticator(payload, machine_id, challenge.challenge, h, db_session))
