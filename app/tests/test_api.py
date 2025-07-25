import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
os.environ["DATABASE_URL"] = SQLALCHEMY_DATABASE_URL

from ..main import app
from ..database import Base, get_db
from .. import models
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
    response = client.post("/users/", json={"email": "user@example.com", "password": "pass"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"

    response = client.post("/auth/token", data={"username": "user@example.com", "password": "pass"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token

from ..version import __version__

def test_version_endpoint():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": __version__}
