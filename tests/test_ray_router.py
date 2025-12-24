from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from api_app.main import app
from api_app import udp


def _configure_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("LOAD_SAMPLE_DATA", "False")
    monkeypatch.setenv("RAY_PASSWORD", "secret-ray")


def test_ray_auth_required(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path)
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ray/ping",
            headers={"x-ray-password": "wrong"},
        )
        assert resp.status_code == 401


def test_discovery_ingest_creates_machine(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path)
    monkeypatch.setattr(udp, "_fetch_machine_uid", AsyncMock(return_value="uid-123"))
    monkeypatch.setattr(udp, "_fetch_machine_version", AsyncMock(return_value="1.0"))

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/ray/discovery",
            json={"ip": "1.2.3.4", "type": "hello", "name": "Test Machine"},
            headers={"x-ray-password": "secret-ray"},
        )
        assert resp.status_code == 200

        machines = client.get("/api/v1/machines/").json()
        assert any(machine["uid"] == "uid-123" for machine in machines)
