import base64
import os

from cryptography.hazmat.primitives.asymmetric import x25519, rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from app import models
from app.websocket_app import generate_code


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

    with ws_client.websocket_connect("/ws/claim") as ws:
        ws.send_json({"client_key": client_key})
        data = ws.receive_json()

    assert {
        "server_key",
        "claim_code",
        "machine_id",
        "signature",
        "claim_url",
    } <= data.keys()
    assert data["claim_url"] == f"https://example.com/claim?code={data['claim_code']}"

    # ensure record stored
    claim = (
        db_session.query(models.MachineClaim)
        .filter_by(machine_id=data["machine_id"])
        .first()
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

    # claim should be marked claimed and retain original code
    db_session.expire_all()
    claim = (
        db_session.query(models.MachineClaim)
        .filter_by(machine_id=data["machine_id"])
        .first()
    )
    assert claim is not None
    assert claim.claimed is True
    assert claim.claim_code == data["claim_code"]

    # status should be linked
    res = client.get(f"/api/machines/{data['machine_id']}/status")
    assert res.status_code == 200
    assert res.json() == {"linked": True}


def test_generate_code_uniqueness():
    codes = {generate_code() for _ in range(100)}
    assert len(codes) == 100


def test_finalize_claim_requires_auth(client):
    res = client.post("/api/claim", json={"code": "FAKE"})
    assert res.status_code == 401


def test_claim_code_remains_valid_after_unauthenticated_attempt(
    client, ws_client, db_session
):
    # generate claim via websocket
    with ws_client.websocket_connect("/ws/claim") as ws:
        data = ws.receive_json()

    code = data["claim_code"]
    machine_id = data["machine_id"]

    # attempt to finalize without authentication
    res = client.post("/api/claim", json={"code": code})
    assert res.status_code == 401

    # ensure claim record untouched
    claim = (
        db_session.query(models.MachineClaim).filter_by(machine_id=machine_id).first()
    )
    assert claim is not None
    assert claim.claimed is False
    assert claim.claim_code == code

    # create and log in user
    client.post(
        "/api/v1/users/",
        json={"email": "auth@example.com", "password": "pass", "screen_name": "auth"},
    )
    token_res = client.post(
        "/api/v1/auth/token",
        data={"username": "auth@example.com", "password": "pass"},
    )
    token = token_res.json()["access_token"]

    # finalize claim successfully
    res = client.post(
        "/api/claim",
        json={"code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 204

    claim = (
        db_session.query(models.MachineClaim).filter_by(machine_id=machine_id).first()
    )
    assert claim.claimed is True
    assert claim.claim_code == code


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
