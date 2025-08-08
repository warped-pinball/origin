import os
import base64
from cryptography.hazmat.primitives.asymmetric import x25519, rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, NoEncryption, PrivateFormat
from app import models
from app.routers.claim import generate_code


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

    assert {"server_key", "claim_code", "machine_id", "signature", "claim_url"} <= data.keys()
    assert data["claim_url"] == f"https://example.com/claim?code={data['claim_code']}"

    # ensure record stored
    claim = db_session.query(models.MachineClaim).filter_by(machine_id=data["machine_id"]).first()
    assert claim is not None

    # create user
    client.post(
        "/api/v1/users/",
        json={"email": "claimer@example.com", "password": "pass", "screen_name": "claimer"},
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


def test_generate_code_uniqueness():
    codes = {generate_code() for _ in range(100)}
    assert len(codes) == 100
