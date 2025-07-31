import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
os.environ["DATABASE_URL"] = SQLALCHEMY_DATABASE_URL
# ensure a clean database for each test run
if os.path.exists("test.db"):
    os.remove("test.db")

from ..main import app
from ..database import Base, get_db
from .. import models
from ..version import __version__
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# Dependency override

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_create_user_and_login():
    response = client.post(
        "/api/v1/users/",
        json={
            "email": "user@example.com",
            "password": "pass",
            "screen_name": "user1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["is_verified"] is False
    # User cannot login before verifying
    response = client.post("/api/v1/auth/token", data={"username": "user@example.com", "password": "pass"})
    assert response.status_code == 403
    # Verify email
    with TestingSessionLocal() as db:
        token = db.query(models.User).filter_by(email="user@example.com").first().verification_token
    client.get(f"/api/v1/auth/verify?token={token}")
    # Login succeeds after verification
    response = client.post("/api/v1/auth/token", data={"username": "user@example.com", "password": "pass"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token


def test_login_user_not_found():
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "missing@example.com", "password": "pass"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_wrong_password():
    # create user
    client.post(
        "/api/v1/users/",
        json={"email": "wp@example.com", "password": "right", "screen_name": "u"},
    )
    with TestingSessionLocal() as db:
        token = db.query(models.User).filter_by(email="wp@example.com").first().verification_token
    client.get(f"/api/v1/auth/verify?token={token}")
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "wp@example.com", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_trailing_space():
    client.post(
        "/api/v1/users/",
        json={"email": "ts@example.com", "password": "pass", "screen_name": "ts"},
    )
    with TestingSessionLocal() as db:
        token = db.query(models.User).filter_by(email="ts@example.com").first().verification_token
    client.get(f"/api/v1/auth/verify?token={token}")
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "ts@example.com ", "password": "pass"},
    )
    assert response.status_code == 200


def test_password_reset_flow():
    client.post(
        "/api/v1/users/",
        json={"email": "reset@example.com", "password": "old", "screen_name": "r"},
    )
    with TestingSessionLocal() as db:
        verify_token = db.query(models.User).filter_by(email="reset@example.com").first().verification_token
    client.get(f"/api/v1/auth/verify?token={verify_token}")
    client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "reset@example.com"},
    )
    with TestingSessionLocal() as db:
        reset_token = db.query(models.User).filter_by(email="reset@example.com").first().reset_token
    client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "password": "new"},
    )
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "reset@example.com", "password": "new"},
    )
    assert response.status_code == 200


def test_root_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Sign Up" in response.text
    assert __version__ in response.text

def test_version_endpoint():
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    assert response.json() == {"version": __version__}
