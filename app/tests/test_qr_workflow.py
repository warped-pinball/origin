from base64 import urlsafe_b64encode
from uuid import uuid4

from .test_user_machines import auth_headers, create_user, login
from .. import models


def _encode_qr_id(qr_id: int) -> str:
    raw = str(qr_id).encode("utf-8")
    return urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _create_qr(db_session) -> tuple[models.QRCode, str]:
    qr = models.QRCode(url="placeholder")
    db_session.add(qr)
    db_session.commit()
    code = _encode_qr_id(qr.id)
    qr.url = f"https://example.com/q?r={code}"
    db_session.add(qr)
    db_session.commit()
    db_session.refresh(qr)
    return qr, code


def _create_machine(
    db_session, owner_id: int, machine_id: str | None = None
) -> models.Machine:
    machine_id = machine_id or f"machine-{uuid4().hex}"
    machine = models.Machine(
        id=machine_id,
        game_title="Owned Machine",
        shared_secret=f"secret-{uuid4().hex}",
        user_id=owner_id,
    )
    db_session.add(machine)
    db_session.commit()
    db_session.refresh(machine)
    return machine


def test_first_scan_claims_qr_for_user(client, db_session):
    owner = create_user(client, "qr-owner@example.com")
    token = login(client, "qr-owner@example.com")
    _create_machine(db_session, owner_id=owner["id"])
    qr, code = _create_qr(db_session)

    response = client.get(f"/q?r={code}", headers=auth_headers(token))

    assert response.status_code == 200
    assert "Select Machine" in response.text
    db_session.refresh(qr)
    assert qr.user_id == owner["id"]


def test_unknown_code_creates_qr_entry(client, db_session):
    owner = create_user(client, "qr-unknown-owner@example.com")
    token = login(client, "qr-unknown-owner@example.com")
    machine = _create_machine(db_session, owner_id=owner["id"], machine_id="machine-unknown")

    code = "AbCdEf12"

    response = client.get(f"/q?r={code}", headers=auth_headers(token))

    assert response.status_code == 200
    assert "Select Machine" in response.text

    qr = (
        db_session.query(models.QRCode)
        .filter(models.QRCode.nfc_link == code)
        .one()
    )
    assert qr.url.endswith(f"/q?r={code}")
    assert qr.user_id == owner["id"]

    assign_response = client.post(
        "/q/assign",
        headers=auth_headers(token),
        data={"code": code, "machine_id": machine.id},
        follow_redirects=False,
    )

    assert assign_response.status_code == 302
    assert assign_response.headers["location"].endswith(f"/machines/{machine.id}")

    db_session.refresh(qr)
    assert qr.machine_id == machine.id


def test_qr_scan_uses_cookie_when_no_auth_header(client, db_session):
    owner = create_user(client, "qr-cookie-owner@example.com")
    login_response = client.post(
        "/api/v1/auth/token",
        data={"username": "qr-cookie-owner@example.com", "password": "pass"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    assert login_response.cookies.get("token") == token

    _create_machine(db_session, owner_id=owner["id"])
    qr, code = _create_qr(db_session)

    response = client.get(f"/q?r={code}", cookies={"token": token})

    assert response.status_code == 200
    assert "Select Machine" in response.text


def test_other_user_cannot_claim_claimed_qr(client, db_session):
    owner = create_user(client, "qr-claimed-owner@example.com")
    owner_token = login(client, "qr-claimed-owner@example.com")
    _create_machine(db_session, owner_id=owner["id"])
    qr, code = _create_qr(db_session)

    response = client.get(f"/q?r={code}", headers=auth_headers(owner_token))
    assert response.status_code == 200

    other = create_user(client, "qr-claimed-other@example.com")
    other_token = login(client, "qr-claimed-other@example.com")

    response = client.get(f"/q?r={code}", headers=auth_headers(other_token))

    assert response.status_code == 404


def test_owner_can_assign_machine_to_claimed_qr(client, db_session):
    owner = create_user(client, "qr-assign-owner@example.com")
    owner_token = login(client, "qr-assign-owner@example.com")
    machine = _create_machine(db_session, owner_id=owner["id"], machine_id="machine-123")
    qr, code = _create_qr(db_session)

    response = client.get(f"/q?r={code}", headers=auth_headers(owner_token))
    assert response.status_code == 200

    response = client.post(
        "/q/assign",
        headers=auth_headers(owner_token),
        data={"code": code, "machine_id": machine.id},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"].endswith(f"/machines/{machine.id}")
    db_session.refresh(qr)
    assert qr.machine_id == machine.id


def test_other_user_scanning_assigned_qr_gets_redirect(client, db_session):
    owner = create_user(client, "qr-redirect-owner@example.com")
    owner_token = login(client, "qr-redirect-owner@example.com")
    machine = _create_machine(db_session, owner_id=owner["id"], machine_id="machine-redirect")
    qr, code = _create_qr(db_session)

    response = client.get(f"/q?r={code}", headers=auth_headers(owner_token))
    assert response.status_code == 200

    assign_response = client.post(
        "/q/assign",
        headers=auth_headers(owner_token),
        data={"code": code, "machine_id": machine.id},
        follow_redirects=False,
    )
    assert assign_response.status_code == 302

    other = create_user(client, "qr-redirect-other@example.com")
    other_token = login(client, "qr-redirect-other@example.com")

    response = client.get(
        f"/q?r={code}",
        headers=auth_headers(other_token),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"].endswith(f"/machines/{machine.id}")
