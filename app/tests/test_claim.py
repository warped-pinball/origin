import base64
import os
import json

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, x25519, rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from app import models
from app.ws import generate_code


def test_machine_claim_flow(client, ws_client, db_session):
    # setup RSA key
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    os.environ["RSA_PRIVATE_KEY"] = pem.decode()

    # generate client key
    client_priv = x25519.X25519PrivateKey.generate()
    client_pub = client_priv.public_key()
    client_key = base64.b64encode(
        client_pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode()

    os.environ["PUBLIC_HOST_URL"] = "https://example.com"

    with ws_client.websocket_connect("/ws/setup") as ws:
        msg = json.dumps({"client_key": client_key})
        ws.send_text(f"handshake|{msg}")
        raw = ws.receive_text()
        route, payload, signature = raw.split("|", 2)
        assert route == "handshake"
        data = json.loads(payload)
        message = f"{route}|{payload}".encode("utf-8")
        priv.public_key().verify(
            base64.b64decode(signature),
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        data["signature"] = signature

    assert {
        "server_key",
        "claim_code",
        "machine_id",
        "signature",
        "claim_url",
    } <= data.keys()
    assert data["claim_url"] == f"https://example.com/claim?code={data['claim_code']}"

    # ensure record stored
    machine_hex = base64.b64decode(data["machine_id"]).hex()
    claim = (
        db_session.query(models.MachineClaim).filter_by(machine_id=machine_hex).first()
    )
    assert claim is not None

    # create user
    client.post(
        "/api/v1/users/",
        json={
            "email": "claimer@example.com",
            "password": "pass",
            "screen_name": "claimer",
        },
    )

    # login user
    token_res = client.post(
        "/api/v1/auth/token",
        data={"username": "claimer@example.com", "password": "pass"},
    )
    assert token_res.status_code == 200
    token = token_res.json()["access_token"]

    # finalize claim
    res = client.post(
        "/api/claim",
        json={"code": data["claim_code"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 204

    # status should be linked
    res = client.get(f"/api/machines/{machine_hex}/status")
    assert res.status_code == 200
    assert res.json() == {"linked": True}


def test_generate_code_uniqueness():
    codes = {generate_code() for _ in range(100)}
    assert len(codes) == 100


def test_finalize_claim_requires_auth(client):
    res = client.post("/api/claim", json={"code": "FAKE"})
    assert res.status_code == 401


def test_claim_page_shows_game_title(client, db_session):
    claim = models.MachineClaim(
        machine_id="m123",
        claim_code="CODE123",
        shared_secret="secret",
        client_game_title="Test Game",
        claimed=False,
    )
    db_session.add(claim)
    db_session.commit()

    res = client.get("/claim", params={"code": "CODE123"})
    assert res.status_code == 200
    assert "Test Game" in res.text
