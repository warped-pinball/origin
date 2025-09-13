from base64 import b64encode
import os

from cryptography.hazmat.primitives.asymmetric import rsa, x25519
from cryptography.hazmat.primitives import serialization

from app import models


def test_handshake_accepts_json_body(client, monkeypatch, db_session):
    # Provide RSA key for signing responses
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    monkeypatch.setenv("RSA_PRIVATE_KEY", pem.decode("ascii"))

    # Generate valid X25519 public key
    priv = x25519.X25519PrivateKey.generate()
    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_b64 = b64encode(pub_bytes).decode("ascii")

    # Client challenge required for signing
    challenge = os.urandom(32)
    headers = {"X-Client-Challenge": b64encode(challenge).decode("ascii")}

    resp = client.post(
        "/api/v1/machines/handshake",
        json={"client_public_key_b64": pub_b64, "game_title": "FishTales_L4"},
        headers=headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert {"machine_id", "claim_url", "server_key", "claim_code"} <= data.keys()

    db_session.query(models.MachineClaim).delete()
    db_session.query(models.Machine).delete()
    db_session.commit()
