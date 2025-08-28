import importlib
import pytest
from sqlalchemy import exc

import app.database as db


def make_dummy_conn():
    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

    return DummyConn()


def test_wait_for_db_retries(monkeypatch):
    importlib.reload(db)
    calls = {"count": 0}

    def connect():
        calls["count"] += 1
        if calls["count"] < 3:
            raise exc.OperationalError("stmt", {}, Exception())
        return make_dummy_conn()

    monkeypatch.setattr(db.engine, "connect", connect)
    db.wait_for_db(max_attempts=5, delay=0)
    assert calls["count"] == 3


def test_wait_for_db_raises(monkeypatch):
    importlib.reload(db)

    def connect():
        raise exc.OperationalError("stmt", {}, Exception())

    monkeypatch.setattr(db.engine, "connect", connect)
    with pytest.raises(exc.OperationalError):
        db.wait_for_db(max_attempts=2, delay=0)
