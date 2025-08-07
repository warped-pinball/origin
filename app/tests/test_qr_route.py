import os
import base64
from .. import models


def _encode_id(i: int) -> str:
    return base64.urlsafe_b64encode(str(i).encode()).decode().rstrip("=")


def _create_user_and_token(client, email="qr@example.com", screen="qruser"):
    client.post(
        "/api/v1/users/",
        json={"email": email, "password": "pass", "screen_name": screen},
    )
    res = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "pass"},
    )
    return res.json()["access_token"], email


def test_qr_redirects_to_machine(client, db_session):
    os.environ["PUBLIC_HOST_URL"] = "https://example.com"
    token, email = _create_user_and_token(client, "owner1@example.com", "user1")
    machine = models.Machine(name="QRM1", secret="s")
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
    assert res.status_code == 302
    assert res.headers["location"] == f"https://example.com/machines/{machine.id}"


def test_qr_requires_configuration(client, db_session):
    os.environ["PUBLIC_HOST_URL"] = "https://example.com"
    token, email = _create_user_and_token(client, "owner2@example.com", "user2")
    user = db_session.query(models.User).filter_by(email=email).first()
    machine = models.Machine(name="QRM2", secret="s", user_id=user.id)
    db_session.add(machine)
    db_session.commit()
    qr = models.QRCode(url="code2")
    db_session.add(qr)
    db_session.commit()
    encoded = _encode_id(qr.id)
    res = client.get(
        f"/q?r={encoded}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert "QRM2" in res.text


def test_qr_requires_machine_setup_message(client, db_session):
    os.environ["PUBLIC_HOST_URL"] = "https://example.com"
    token, email = _create_user_and_token(client, "owner3@example.com", "user3")
    qr = models.QRCode(url="code3")
    db_session.add(qr)
    db_session.commit()
    encoded = _encode_id(qr.id)
    res = client.get(
        f"/q?r={encoded}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert "No machines are currently registered to your account" in res.text


def test_qr_assign_endpoint(client, db_session):
    os.environ["PUBLIC_HOST_URL"] = "https://example.com"
    token, email = _create_user_and_token(client, "owner4@example.com", "user4")
    user = db_session.query(models.User).filter_by(email=email).first()
    machine = models.Machine(name="QRM3", secret="s", user_id=user.id)
    db_session.add(machine)
    db_session.commit()
    qr = models.QRCode(url="code4", user_id=user.id)
    db_session.add(qr)
    db_session.commit()
    encoded = _encode_id(qr.id)
    res = client.post(
        "/q/assign",
        data={"code": encoded, "machine_id": machine.id},
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert res.headers["location"] == f"https://example.com/machines/{machine.id}"
    db_session.refresh(qr)
    assert qr.machine_id == machine.id


def test_qr_invalid_code(client):
    token, _ = _create_user_and_token(client, "owner5@example.com", "user5")
    res = client.get(
        "/q?r=notbase64!",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Invalid code"


def test_qr_redirects_to_login_when_unauthenticated(client):
    encoded = _encode_id(1)
    res = client.get(f"/q?r={encoded}", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == f"/?next=%2Fq%3Fr%3D{encoded}"
