import os
import base64
from cryptography.hazmat.primitives.asymmetric import x25519, rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, NoEncryption, PrivateFormat
from .test_api import client, ws_client, TestingSessionLocal
from app import models


def test_machine_claim_flow():
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

    with ws_client.websocket_connect("/ws/claim") as ws:
        ws.send_json({"client_key": client_key})
        data = ws.receive_json()

    assert {"server_key", "claim_code", "machine_id", "signature"} <= data.keys()

    # ensure record stored
    db = TestingSessionLocal()
    try:
        claim = db.query(models.MachineClaim).filter_by(machine_id=data["machine_id"]).first()
        assert claim is not None
    finally:
        db.close()

    # create user
    client.post(
        "/api/v1/users/",
        json={"email": "claim@example.com", "password": "pass", "screen_name": "claimer"},
    )

    # finalize claim
    res = client.post(
        "/api/claim", json={"code": data["claim_code"], "user_id": 1}
    )
    assert res.status_code == 204

    # status should be linked
    res = client.get(f"/api/machines/{data['machine_id']}/status")
    assert res.status_code == 200
    assert res.json() == {"linked": True}
