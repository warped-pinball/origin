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

    response = client.post("/api/v1/auth/token", data={"username": "user@example.com", "password": "pass"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token


def test_root_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Sign Up" in response.text
    assert __version__ in response.text

def test_version_endpoint():
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    assert response.json() == {"version": __version__}
