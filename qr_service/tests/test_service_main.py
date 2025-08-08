import importlib
import sys
from pathlib import Path

import xml.etree.ElementTree as ET
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
    monkeypatch.setenv("QR_PRINT_WIDTH_IN", "2.5")
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.post("/generate", json={"count": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert "sheet" not in data
        for item in data["items"]:
            assert item["url"].startswith("https://example.com/")
            root = ET.fromstring(item["svg"])
            assert root.get("width") == "2.5in"
            assert root.get("height").endswith("in")


def test_generate_respects_random_len(monkeypatch):
    monkeypatch.setenv("QR_BASE_URL", "https://example.com")
    monkeypatch.setenv("QR_RANDOM_LEN", "17")
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.post("/generate", json={"count": 1})
        assert resp.status_code == 200
        data = resp.json()
        suffix = data["items"][0]["suffix"]
        assert len(suffix) == 17
        assert data["items"][0]["url"].endswith(suffix)


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
        assert "Download" in text
