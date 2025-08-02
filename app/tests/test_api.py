import subprocess
from fastapi import FastAPI
from fastapi.testclient import TestClient
from .. import models
from ..version import __version__



def test_create_user_and_login(client):
    response = client.post(
        "/api/v1/users/",
        json={
            "phone": "+10000000001",
            "password": "pass",
            "screen_name": "user1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "+10000000001"
    assert data["is_verified"] is True
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "+10000000001", "password": "pass"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token


def test_login_user_not_found(client):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "+19999999999", "password": "pass"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid phone or password"


def test_login_wrong_password(client):
    client.post(
        "/api/v1/users/",
        json={"phone": "+10000000002", "password": "right", "screen_name": "u"},
    )
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "+10000000002", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid phone or password"


def test_login_trailing_space(client):
    client.post(
        "/api/v1/users/",
        json={"phone": "+10000000003", "password": "pass", "screen_name": "ts"},
    )
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "+10000000003 ", "password": "pass"},
    )
    assert response.status_code == 200


def test_login_unverified_user(client, db_session):
    from .. import crud, schemas
    user = schemas.UserCreate(phone="+10000000005", password="pass", screen_name="u")
    crud.create_user(db_session, user)
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "+10000000005", "password": "pass"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Phone not verified"


def test_sms_sent_when_configured(client, monkeypatch):
    from ..routers import users

    sent = {}

    monkeypatch.setattr(users, "is_sms_configured", lambda: True)

    def fake_send(phone, token):
        sent["phone"] = phone
        sent["token"] = token

    monkeypatch.setattr(users, "send_verification_sms", fake_send)

    response = client.post(
        "/api/v1/users/",
        json={"phone": "+10000000006", "password": "pass", "screen_name": "u"},
    )

    assert response.status_code == 200
    assert response.json()["is_verified"] is False
    assert sent["phone"] == "+10000000006"
    assert sent["token"]


def test_password_reset_flow(client, db_session):
    client.post(
        "/api/v1/users/",
        json={"phone": "+10000000004", "password": "old", "screen_name": "r"},
    )
    client.post(
        "/api/v1/auth/password-reset/request",
        json={"phone": "+10000000004"},
    )
    reset_token = db_session.query(models.User).filter_by(phone="+10000000004").first().reset_token
    client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "password": "new"},
    )
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "+10000000004", "password": "new"},
    )
    assert response.status_code == 200


def test_root_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Sign Up" in response.text
    assert __version__ in response.text
    assert '<meta name="description" content="Origin web application">' in response.text
    assert '<html lang="en"' in response.text


def test_gzip_enabled(client):
    response = client.get("/", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"


def test_version_endpoint(client):
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    assert response.json() == {"version": __version__}
