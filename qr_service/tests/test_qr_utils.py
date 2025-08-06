import xml.etree.ElementTree as ET

from qr_service.service.qr import random_suffix, generate_svg, add_frame


def test_random_suffix_length():
    assert len(random_suffix(12)) == 12


def test_random_suffix_uniqueness():
    vals = {random_suffix(8) for _ in range(50)}
    assert len(vals) == 50


def test_generate_svg_has_dimensions():
    svg = generate_svg("data")
    assert svg.startswith("<svg")
    assert 'width="300"' in svg
    assert 'height="300"' in svg


def test_generate_svg_custom_color(monkeypatch):
    monkeypatch.setenv("QR_CODE_COLOR", "#123456")
    svg = generate_svg("data")
    assert "#123456" in svg


def test_add_frame_removes_namespace_prefixes():
    inner = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300"></svg>'
    framed = add_frame(inner)
    assert 'ns0:' not in framed
    assert 'svg:' not in framed


def test_add_frame_env_customizations(monkeypatch):
    monkeypatch.setenv("QR_CODE_BACKGROUND_COLOR", "#abcdef")
    monkeypatch.setenv("QR_FRAME_BACKGROUND_COLOR", "#111111")
    monkeypatch.setenv("QR_FRAME_COLOR", "#222222")
    monkeypatch.setenv("QR_TEXT_COLOR", "#333333")
    monkeypatch.setenv("QR_TOP_TEXT", "Top")
    monkeypatch.setenv("QR_BOTTOM_TEXT", "Bottom")
    svg = add_frame(generate_svg("data"))
    assert "#abcdef" in svg
    assert "#111111" in svg
    assert "#222222" in svg
    assert "#333333" in svg
    assert "Top" in svg
    assert "Bottom" in svg


def test_add_frame_padding_and_style(monkeypatch):
    monkeypatch.setenv("QR_FRAME_PADDING_MODULES", "1")
    svg = add_frame(generate_svg("data"))
    root = ET.fromstring(svg)
    rects = root.findall("{http://www.w3.org/2000/svg}rect")
    inner_rect = [r for r in rects if r.get("x") == "20" and r.get("y") == "40"][0]
    assert float(inner_rect.get("width")) > 300
    border = [r for r in rects if r.get("stroke")][0]
    assert border.get("stroke-width") == "1"
    assert "stroke-dasharray" not in border.attrib
    assert border.get("rx") == border.get("ry")


def test_separate_corner_radii(monkeypatch):
    monkeypatch.setenv("QR_FRAME_CORNER_RADIUS", "10")
    monkeypatch.setenv("QR_CODE_CORNER_RADIUS", "5")
    svg = add_frame(generate_svg("data"))
    root = ET.fromstring(svg)
    rects = root.findall("{http://www.w3.org/2000/svg}rect")
    outer_rect = [r for r in rects if r.get("x") == "0" and r.get("y") == "0"][0]
    inner_rect = [r for r in rects if r.get("x") == "20" and r.get("y") == "40"][0]
    assert float(outer_rect.get("rx")) == 10
    assert float(inner_rect.get("rx")) == 5


def test_logo_included(monkeypatch):
    monkeypatch.setenv("QR_LOGO_IMAGE", "logo.png")
    monkeypatch.setenv("QR_LOGO_SCALE", "0.2")
    svg = add_frame(generate_svg("data"))
    root = ET.fromstring(svg)
    images = root.findall("{http://www.w3.org/2000/svg}image")
    assert images and images[0].get("{http://www.w3.org/1999/xlink}href") == "logo.png"


def test_module_drawer_generates_image(monkeypatch):
    monkeypatch.setenv("QR_MODULE_DRAWER", "rounded")
    svg = generate_svg("data")
    root = ET.fromstring(svg)
    images = root.findall("{http://www.w3.org/2000/svg}image")
    assert images and images[0].get("{http://www.w3.org/1999/xlink}href").startswith(
        "data:image/png;base64,"
    )


def test_framed_svg_uses_xlink_prefix(monkeypatch):
    monkeypatch.setenv("QR_MODULE_DRAWER", "rounded")
    svg = add_frame(generate_svg("data"))
    assert "ns0:href" not in svg
    assert "xlink:href" in svg
