import importlib
import pytest


def test_app_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        importlib.reload(importlib.import_module("app.auth"))
