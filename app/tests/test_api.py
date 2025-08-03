import subprocess
from fastapi import FastAPI
from fastapi.testclient import TestClient
from .. import models
from ..version import __version__



def test_create_user_and_login(client):
    response = client.post(
        "/api/v1/users/",
        json={
            "email": "user1@example.com",
            "password": "pass",
            "screen_name": "user1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user1@example.com"
    assert data["is_verified"] is True
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "user1@example.com", "password": "pass"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token


def test_create_user_duplicate_screen_name_allowed(client):
    """Users can share the same screen name as long as emails differ."""
    response1 = client.post(
        "/api/v1/users/",
        json={"email": "dup1@example.com", "password": "pass", "screen_name": "dupe"},
    )
    assert response1.status_code == 200
    response2 = client.post(
        "/api/v1/users/",
        json={"email": "dup2@example.com", "password": "pass", "screen_name": "dupe"},
    )
    assert response2.status_code == 200


def test_create_user_duplicate_email(client):
    client.post(
        "/api/v1/users/",
        json={"email": "dup@example.com", "password": "pass", "screen_name": "user1"},
    )
    response = client.post(
        "/api/v1/users/",
        json={"email": "dup@example.com", "password": "pass", "screen_name": "user2"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


def test_login_user_not_found(client):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "missing@example.com", "password": "pass"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_wrong_password(client):
    client.post(
        "/api/v1/users/",
        json={"email": "user2@example.com", "password": "right", "screen_name": "u"},
    )
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "user2@example.com", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_trailing_space(client):
    client.post(
        "/api/v1/users/",
        json={"email": "user3@example.com", "password": "pass", "screen_name": "ts"},
    )
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "user3@example.com ", "password": "pass"},
    )
    assert response.status_code == 200


def test_login_unverified_user(client, db_session):
    from .. import crud, schemas
    user = schemas.UserCreate(email="user5@example.com", password="pass", screen_name="u")
    crud.create_user(db_session, user)
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "user5@example.com", "password": "pass"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Email not verified"


def test_password_reset_flow(client, db_session):
    client.post(
        "/api/v1/users/",
        json={"email": "user4@example.com", "password": "old", "screen_name": "r"},
    )
    client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "user4@example.com"},
    )
    reset_token = db_session.query(models.User).filter_by(email="user4@example.com").first().reset_token
    client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "password": "new"},
    )
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "user4@example.com", "password": "new"},
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


def test_root_contains_tournament_ui(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Create Tournament" in response.text
