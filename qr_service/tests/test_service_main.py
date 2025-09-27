import importlib
import sys
from pathlib import Path

import base64
import xml.etree.ElementTree as ET
from io import BytesIO
from fastapi.testclient import TestClient
from PIL import Image
from qr_service.service.qr import TEMPLATES_DIR
import pytest
import zipfile


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
    monkeypatch.setenv("QR_PREVIEW_SCALE", "0.5")
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.post("/generate", json={"count": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert "preview" in data and "download_id" in data
        item = data["preview"]
        assert item["url"].startswith("https://example.com/")
        assert "before_svg" in item and "after_svg" in item

        after_root = ET.fromstring(item["after_svg"])
        assert after_root.get("width").endswith("in")
        assert float(after_root.get("width")[:-2]) == pytest.approx(1.25)

        before_root = ET.fromstring(item["before_svg"])
        assert before_root.get("width").endswith("in")

        # test download
        resp2 = client.get(f"/download/{data['download_id']}")
        assert resp2.status_code == 200
        z = zipfile.ZipFile(BytesIO(resp2.content))
        assert len(z.namelist()) == 2
        content = z.read(z.namelist()[0]).decode()
        final_root = ET.fromstring(content)
        assert final_root.get("width") == "2.5in"
        assert final_root.get("height").endswith("in")
        assert not any(elem.attrib.get("stroke") == "#ff0000" for elem in final_root.iter())


def test_generate_applies_post_processing(monkeypatch):
    monkeypatch.setenv("QR_BASE_URL", "https://example.com")
    monkeypatch.setenv("QR_PRINT_WIDTH_IN", "2.0")
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.post(
            "/generate",
            json={
                "count": 1,
                "saturation_boost": 0.4,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        preview = data["preview"]
        after_root = ET.fromstring(preview["after_svg"])
        ns = {"svg": "http://www.w3.org/2000/svg"}
        group = after_root.find("svg:g", ns)
        assert group is not None and "filter" in group.attrib

        resp2 = client.get(f"/download/{data['download_id']}")
        assert resp2.status_code == 200
        z = zipfile.ZipFile(BytesIO(resp2.content))
        final_content = z.read(z.namelist()[0]).decode()
        final_root = ET.fromstring(final_content)
        defs = final_root.find("svg:defs", ns)
        assert defs is not None
        morph = final_root.find(".//svg:feMorphology", ns)
        assert morph is None
        color_matrix = final_root.find(".//svg:feColorMatrix", ns)
        assert color_matrix is not None
        assert color_matrix.get("type") == "saturate"


def test_generate_url_does_not_force_slash(monkeypatch):
    monkeypatch.setenv("QR_BASE_URL", "https://example.com/?token=")
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.post("/generate", json={"count": 1})
        assert resp.status_code == 200
        data = resp.json()["preview"]
        assert data["url"] == f"https://example.com/?token={data['suffix']}"


def test_generate_precomputes_suffixes(monkeypatch):
    monkeypatch.setenv("QR_BASE_URL", "https://example.com")
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    seq = iter(["aa", "bb"])
    monkeypatch.setattr(main, "random_suffix", lambda n: next(seq))

    with TestClient(main.app) as client:
        resp = client.post("/generate", json={"count": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert data["preview"]["suffix"] == "aa"
        resp2 = client.get(f"/download/{data['download_id']}")
        z = zipfile.ZipFile(BytesIO(resp2.content))
        names = sorted(n[:-4] for n in z.namelist())
        assert names == ["aa", "bb"]


def test_generate_with_template(monkeypatch):
    monkeypatch.setenv("QR_BASE_URL", "https://example.com")
    monkeypatch.setenv("QR_MODULE_DRAWER", "rounded")
    monkeypatch.setenv("QR_TEMPLATE_SCALE", "0.5")
    monkeypatch.setenv("QR_PRINT_WIDTH_IN", "1.5")
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.post("/generate", json={"count": 1, "template": "white.png"})
        assert resp.status_code == 200
        payload = resp.json()
        preview = payload["preview"]
        root = ET.fromstring(preview["after_svg"])
        assert not root.findall("{http://www.w3.org/2000/svg}text")
        inner = root.find("{http://www.w3.org/2000/svg}svg")
        assert inner is not None
        view = [float(v) for v in root.get("viewBox").split()]
        w = view[2]
        h = view[3]
        size = float(inner.get("width"))
        assert float(inner.get("x")) == (w - size) / 2
        assert float(inner.get("y")) == (h - size) / 2
        assert root.get("width") == "1.5in"
        assert root.get("height").endswith("in")
        assert not any(elem.attrib.get("stroke") == "#ff0000" for elem in root.iter())

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

        resp2 = client.get(f"/download/{payload['download_id']}")
        assert resp2.status_code == 200
        archive = zipfile.ZipFile(BytesIO(resp2.content))
        final_root = ET.fromstring(archive.read(archive.namelist()[0]).decode())
        assert final_root.get("width") == "1.5in"
        assert final_root.get("height").endswith("in")


def test_generate_with_template_and_offset(monkeypatch):
    monkeypatch.setenv("QR_BASE_URL", "https://example.com")
    monkeypatch.setenv("QR_TEMPLATE_OFFSET", "0.4")
    for mod in ["qr_service.service.main"]:
        sys.modules.pop(mod, None)
    import qr_service.service.main as main

    with TestClient(main.app) as client:
        resp = client.post("/generate", json={"count": 1, "template": "white.png"})
        assert resp.status_code == 200
        root = ET.fromstring(resp.json()["preview"]["after_svg"])
        inner = root.find("{http://www.w3.org/2000/svg}svg")
        assert inner is not None
        h = float(root.get("viewBox").split()[3])
        size = float(inner.get("height"))
        assert float(inner.get("y")) == pytest.approx(h * 0.4 - size / 2)
        assert not any(elem.attrib.get("stroke") == "#ff0000" for elem in root.iter())


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
        suffix = data["preview"]["suffix"]
        assert len(suffix) == 17
        assert data["preview"]["url"].endswith(suffix)


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
        assert "Saturation" in text
        assert "Erode" not in text
