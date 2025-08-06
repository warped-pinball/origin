import importlib
import os
from sqlalchemy import Table, Column, Integer
from fastapi.testclient import TestClient


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
