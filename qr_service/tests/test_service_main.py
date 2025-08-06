import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def test_fallback_imports_service_qr(tmp_path, monkeypatch):
    """Simulate running from container where service is top-level."""
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root))

    for mod in ["service.main", "service", "qr"]:
        sys.modules.pop(mod, None)

    main = importlib.import_module("service.main")
    qr_mod = importlib.import_module("service.qr")

    assert main.generate_svg is qr_mod.generate_svg


def test_generate_endpoint(monkeypatch):
    monkeypatch.setenv("QR_BASE_URL", "https://example.com")
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.post("/generate", json={"count": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        for item in data["items"]:
            assert item["url"].startswith("https://example.com/")
            assert item["svg"].startswith("<svg")


def test_index_contains_controls(monkeypatch):
    monkeypatch.setenv("QR_BASE_URL", "https://example.com")
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        text = resp.text
        assert "Generate" in text
        assert "count" in text
        assert "cols" in text
