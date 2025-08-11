import importlib

import pytest


def test_app_requires_secret_key(monkeypatch):
    """Verify the auth module fails without SECRET_KEY and restores afterwards."""
    auth = importlib.import_module("app.auth")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        importlib.reload(auth)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    importlib.reload(auth)
