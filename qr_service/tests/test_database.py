import importlib
import os


def test_engine_uses_postgresql(monkeypatch):
    original_url = os.environ.get("DATABASE_URL")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@db/postgres")
    import qr_service.database as database
    importlib.reload(database)
    try:
        assert database.engine.name == "postgresql"
    finally:
        if original_url is None:
            monkeypatch.delenv("DATABASE_URL", raising=False)
        else:
            monkeypatch.setenv("DATABASE_URL", original_url)
        importlib.reload(database)
