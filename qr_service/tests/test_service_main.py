import importlib
import sys
from pathlib import Path

import base64
import xml.etree.ElementTree as ET
from io import BytesIO
from fastapi.testclient import TestClient
from PIL import Image
from qr_service.service.qr import TEMPLATES_DIR
import qr_service.service.qr as qr_module
import pytest


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


def test_generate_with_template(monkeypatch):
    monkeypatch.setenv("QR_BASE_URL", "https://example.com")
    monkeypatch.setenv("QR_MODULE_DRAWER", "rounded")
    monkeypatch.setenv("QR_TEMPLATE_SCALE", "0.5")
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.post("/generate", json={"count": 1, "template": "white.png"})
        assert resp.status_code == 200
        svg = resp.json()["items"][0]["svg"]
        root = ET.fromstring(svg)
        assert not root.findall("{http://www.w3.org/2000/svg}text")
        inner = root.find("{http://www.w3.org/2000/svg}svg")
        assert inner is not None
        w = float(root.get("width"))
        h = float(root.get("height"))
        size = float(inner.get("width"))
        assert float(inner.get("x")) == (w - size) / 2
        assert float(inner.get("y")) == (h - size) / 2

        with Image.open(TEMPLATES_DIR / "white.png") as img:
            orig_w, orig_h = img.size
        assert w == orig_w * 0.5
        assert h == orig_h * 0.5

        ns = {
            "svg": "http://www.w3.org/2000/svg",
            "xlink": "http://www.w3.org/1999/xlink",
        }
        image = inner.find("svg:image", ns)
        assert image is not None
        href = image.get("{http://www.w3.org/1999/xlink}href")
        data = base64.b64decode(href.split(",", 1)[1])
        img = Image.open(BytesIO(data))
        assert img.mode == "RGBA"
        assert img.getchannel("A").getextrema()[0] == 0


def test_generate_with_logo(monkeypatch, tmp_path):
    monkeypatch.setenv("QR_BASE_URL", "https://example.com")
    logo_dir = tmp_path / "logos"
    logo_dir.mkdir()
    path = logo_dir / "logo.png"
    Image.new("RGB", (10, 10), color="red").save(path)
    monkeypatch.setattr(qr_module, "LOGOS_DIR", logo_dir)
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.post("/generate", json={"count": 1, "logo": "logo.png"})
        assert resp.status_code == 200
        svg = resp.json()["items"][0]["svg"]
        root = ET.fromstring(svg)
        inner = root.find("{http://www.w3.org/2000/svg}svg")
        assert inner is not None
        ns = {
            "svg": "http://www.w3.org/2000/svg",
            "xlink": "http://www.w3.org/1999/xlink",
        }
        image = inner.find("svg:image", ns)
        assert image is not None


def test_generate_with_svg_logo(monkeypatch, tmp_path):
    monkeypatch.setenv("QR_BASE_URL", "https://example.com")
    logo_dir = tmp_path / "logos"
    logo_dir.mkdir()
    path = logo_dir / "logo.svg"
    path.write_text(
        "<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'>"
        "<rect width='10' height='10' fill='red'/></svg>"
    )
    monkeypatch.setattr(qr_module, "LOGOS_DIR", logo_dir)
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.post("/generate", json={"count": 1, "logo": "logo.svg"})
        assert resp.status_code == 200
        svg = resp.json()["items"][0]["svg"]
        root = ET.fromstring(svg)
        inner = root.find("{http://www.w3.org/2000/svg}svg")
        assert inner is not None
        ns = {"svg": "http://www.w3.org/2000/svg", "xlink": "http://www.w3.org/1999/xlink"}
        image = inner.find("svg:image", ns)
        assert image is not None
        href = image.get("{http://www.w3.org/1999/xlink}href")
        data = base64.b64decode(href.split(",", 1)[1])
        embedded = Image.open(BytesIO(data)).convert("RGB")
        assert (255, 0, 0) in embedded.getdata()


def test_generate_with_template_and_offset(monkeypatch):
    monkeypatch.setenv("QR_BASE_URL", "https://example.com")
    monkeypatch.setenv("QR_TEMPLATE_OFFSET", "0.4")
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.post("/generate", json={"count": 1, "template": "white.png"})
        assert resp.status_code == 200
        svg = resp.json()["items"][0]["svg"]
        root = ET.fromstring(svg)
        inner = root.find("{http://www.w3.org/2000/svg}svg")
        assert inner is not None
        h = float(root.get("height"))
        size = float(inner.get("height"))
        assert float(inner.get("y")) == pytest.approx(h * 0.4 - size / 2)


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
        assert "template" in text
        assert "logo" in text
