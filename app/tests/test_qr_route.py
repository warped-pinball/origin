import os
import base64
from .. import models


def _encode_id(i: int) -> str:
    return base64.urlsafe_b64encode(str(i).encode()).decode().rstrip("=")


def _create_user_and_token(client):
    client.post(
        "/api/v1/users/",
        json={"email": "qr@example.com", "password": "pass", "screen_name": "qruser"},
    )
    res = client.post(
        "/api/v1/auth/token",
        data={"username": "qr@example.com", "password": "pass"},
    )
    return res.json()["access_token"]


def test_qr_redirects_to_machine(client, db_session):
    os.environ["PUBLIC_HOST_URL"] = "https://example.com"
    token = _create_user_and_token(client)
    machine = models.Machine(name="M1", secret="s")
    db_session.add(machine)
    db_session.commit()
    db_session.refresh(machine)
    qr = models.QRCode(url="code1", machine_id=machine.id)
    db_session.add(qr)
    db_session.commit()
    encoded = _encode_id(qr.id)
    res = client.get(
        f"/q?r={encoded}",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )
    assert res.status_code == 307
    assert res.headers["location"] == f"https://example.com/machines/{machine.id}"


def test_qr_requires_configuration(client, db_session):
    os.environ["PUBLIC_HOST_URL"] = "https://example.com"
    token = _create_user_and_token(client)
    qr = models.QRCode(url="code2")
    db_session.add(qr)
    db_session.commit()
    encoded = _encode_id(qr.id)
    res = client.get(
        f"/q?r={encoded}",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )
    assert res.status_code == 307
    assert res.headers["location"] == f"https://example.com/machines/assign?code={encoded}"


def test_qr_invalid_code(client):
    token = _create_user_and_token(client)
    res = client.get(
        "/q?r=notbase64!",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Invalid code"
