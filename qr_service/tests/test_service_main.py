import importlib
import os
from sqlalchemy import Table, Column, Integer
from fastapi.testclient import TestClient
import sys
from pathlib import Path


def test_pending_endpoint_initializes_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    original_url = os.environ.get("DATABASE_URL")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    import qr_service.database as database
    importlib.reload(database)
    Table('users', database.Base.metadata, Column('id', Integer, primary_key=True))
    Table('machines', database.Base.metadata, Column('id', Integer, primary_key=True))
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
