import importlib
import os
from fastapi.testclient import TestClient
import sys
from pathlib import Path


def test_pending_endpoint_initializes_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    original_url = os.environ.get("DATABASE_URL")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    import qr_service.database as database
    importlib.reload(database)
    import qr_service.models as models
    importlib.reload(models)
    import qr_service.service.main as main
    importlib.reload(main)

    try:
        with TestClient(main.app) as client:
            resp = client.get("/pending")
            assert resp.status_code == 200
            assert resp.json() == {"svgs": []}
    finally:
        if original_url is None:
            monkeypatch.delenv("DATABASE_URL", raising=False)
        else:
            monkeypatch.setenv("DATABASE_URL", original_url)
        importlib.reload(database)
        importlib.reload(models)
        importlib.reload(main)


def test_fallback_imports_service_qr(tmp_path, monkeypatch):
    """Simulate running from container where service is top-level."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    # Add path to mimic container /app layout with service at top level
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root))

    # Ensure a fresh import without existing package context
    for mod in ["service.main", "service", "database", "models"]:
        sys.modules.pop(mod, None)

    main = importlib.import_module("service.main")
    qr_mod = importlib.import_module("service.qr")

    # If fallback worked, main should use service.qr's functions
    assert main.generate_svg is qr_mod.generate_svg


def test_bulk_link_creation(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    original_url = os.environ.get("DATABASE_URL")
    original_base = os.environ.get("QR_BASE_URL")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("QR_BASE_URL", "https://example.com")

    for mod in ["qr_service.database", "qr_service.models", "qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.database as database
    import qr_service.models as models
    import qr_service.service.main as main

    try:
        with TestClient(main.app) as client:
            resp = client.post("/links/bulk", json={"count": 3})
            assert resp.status_code == 200
            assert len(resp.json()["links"]) == 3
            with main.SessionLocal() as session:
                assert session.query(main.QRCode).count() == 3
    finally:
        if original_url is None:
            monkeypatch.delenv("DATABASE_URL", raising=False)
        else:
            monkeypatch.setenv("DATABASE_URL", original_url)
        if original_base is None:
            monkeypatch.delenv("QR_BASE_URL", raising=False)
        else:
            monkeypatch.setenv("QR_BASE_URL", original_base)
        for mod in ["qr_service.database", "qr_service.models", "qr_service.service.main"]:
            sys.modules.pop(mod, None)


def test_index_contains_controls(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    original_url = os.environ.get("DATABASE_URL")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    for mod in ["qr_service.database", "qr_service.models", "qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.database as database
    import qr_service.models as models
    import qr_service.service.main as main

    try:
        with TestClient(main.app) as client:
            resp = client.get("/")
            assert resp.status_code == 200
            text = resp.text
            assert "Generate" in text
            assert "count" in text
            assert "cols" in text
    finally:
        if original_url is None:
            monkeypatch.delenv("DATABASE_URL", raising=False)
        else:
            monkeypatch.setenv("DATABASE_URL", original_url)
        for mod in ["qr_service.database", "qr_service.models", "qr_service.service.main"]:
            sys.modules.pop(mod, None)
