import base64
import xml.etree.ElementTree as ET
from io import BytesIO

import pytest
from PIL import Image, ImageColor

import qr_service.service.qr as qr_module

from qr_service.service.qr import (
    random_suffix,
    generate_svg,
    add_frame,
    apply_template,
    TEMPLATES_DIR,
    prepare_svg_variants,
)


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


def test_alignment_boxes_rounded():
    svg = generate_svg("data")
    root = ET.fromstring(svg)
    path = root.find("{http://www.w3.org/2000/svg}path")
    assert path is not None
    assert "A" in path.attrib.get("d", "")


def test_eye_drawer_square(monkeypatch):
    monkeypatch.setenv("QR_EYE_DRAWER", "square")
    svg = generate_svg("data")
    root = ET.fromstring(svg)
    path = root.find("{http://www.w3.org/2000/svg}path")
    assert path is not None
    assert "A" not in path.attrib.get("d", "")


def test_generate_svg_error_correction(monkeypatch):
    import qrcode as qr_lib

    captured = {}
    orig = qr_lib.QRCode

    def capture_qrcode(*args, **kwargs):
        captured["ec"] = kwargs.get("error_correction")
        return orig(*args, **kwargs)

    monkeypatch.setattr(qr_lib, "QRCode", capture_qrcode)
    monkeypatch.setenv("QR_ERROR_CORRECTION", "H")

    generate_svg("data")
    assert captured["ec"] == qr_lib.constants.ERROR_CORRECT_H


def test_add_frame_removes_namespace_prefixes():
    inner = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300"></svg>'
    framed = add_frame(inner)
    assert "ns0:" not in framed
    assert "svg:" not in framed


def test_add_frame_env_customizations(monkeypatch):
    monkeypatch.setenv("QR_CODE_BACKGROUND_COLOR", "#abcdef")
    monkeypatch.setenv("QR_FRAME_BACKGROUND_COLOR", "#111111")
    svg = add_frame(generate_svg("data"))
    assert "#abcdef" in svg
    assert "#111111" in svg
    assert "#ff0000" not in svg


def test_add_frame_padding_and_style(monkeypatch):
    monkeypatch.setenv("QR_FRAME_PADDING_MODULES", "1")
    svg = add_frame(generate_svg("data"))
    root = ET.fromstring(svg)
    rects = root.findall("{http://www.w3.org/2000/svg}rect")
    inner_rect = [r for r in rects if r.get("x") == "20" and r.get("y") == "40"][0]
    assert float(inner_rect.get("width")) > 300
    assert all(r.get("stroke") in (None, "none") for r in rects)


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
    assert not any(r.get("x") == "2" and r.get("y") == "2" for r in rects)


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


def test_module_drawer_respects_colors(monkeypatch):
    monkeypatch.setenv("QR_MODULE_DRAWER", "rounded")
    monkeypatch.setenv("QR_CODE_COLOR", "#123456")
    monkeypatch.setenv("QR_CODE_BACKGROUND_COLOR", "#abcdef")
    svg = generate_svg("data")
    root = ET.fromstring(svg)
    href = root.findall("{http://www.w3.org/2000/svg}image")[0].get(
        "{http://www.w3.org/1999/xlink}href"
    )
    data = href.split(",", 1)[1]
    img = Image.open(BytesIO(base64.b64decode(data))).convert("RGB")
    fg = ImageColor.getrgb("#123456")
    assert any(pixel == fg for pixel in img.getdata())


def test_circle_drawer_returns_svg(monkeypatch):
    monkeypatch.setenv("QR_MODULE_DRAWER", "circle")
    svg = generate_svg("data")
    root = ET.fromstring(svg)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    assert not root.findall("svg:image", ns)
    assert root.findall("svg:path", ns)


def test_raster_scale_increases_resolution(monkeypatch):
    monkeypatch.setenv("QR_MODULE_DRAWER", "rounded")
    monkeypatch.setenv("QR_RASTER_SCALE", "5")
    svg = generate_svg("data")
    root = ET.fromstring(svg)
    ns = {
        "svg": "http://www.w3.org/2000/svg",
        "xlink": "http://www.w3.org/1999/xlink",
    }
    href = root.find("svg:image", ns).get("{http://www.w3.org/1999/xlink}href")
    data = base64.b64decode(href.split(",", 1)[1])
    img = Image.open(BytesIO(data))
    assert img.width > 300


def test_framed_svg_uses_xlink_prefix(monkeypatch):
    monkeypatch.setenv("QR_MODULE_DRAWER", "rounded")
    svg = add_frame(generate_svg("data"))
    assert "ns0:href" not in svg
    assert "xlink:href" in svg


def test_apply_template_centers_qr():
    inner = generate_svg("data")
    svg = apply_template(inner, "white.png")
    root = ET.fromstring(svg)
    assert not root.findall("{http://www.w3.org/2000/svg}text")
    inner_svg = root.find("{http://www.w3.org/2000/svg}svg")
    assert inner_svg is not None
    view = [float(v) for v in root.get("viewBox").split()]
    width = view[2]
    height = view[3]
    size = float(inner_svg.get("width"))
    assert float(inner_svg.get("x")) == (width - size) / 2
    assert float(inner_svg.get("y")) == (height - size) / 2
    assert root.get("width").endswith("in")
    assert root.get("height").endswith("in")


def test_apply_template_vertical_offset(monkeypatch, tmp_path):
    monkeypatch.setattr(qr_module, "TEMPLATES_DIR", tmp_path)
    path = tmp_path / "test.png"
    Image.new("RGB", (500, 500), color="white").save(path)
    monkeypatch.setenv("QR_TEMPLATE_OFFSET", "0.4")
    inner = generate_svg("data")
    svg = apply_template(inner, path.name)
    root = ET.fromstring(svg)
    inner_svg = root.find("{http://www.w3.org/2000/svg}svg")
    assert inner_svg is not None
    assert float(inner_svg.get("y")) == pytest.approx(50.0)


def test_apply_template_respects_scale(monkeypatch):
    monkeypatch.setenv("QR_TEMPLATE_SCALE", "0.5")
    monkeypatch.setenv("QR_PRINT_WIDTH_IN", "1.5")
    inner = generate_svg("data")
    svg = apply_template(inner, "white.png")
    root = ET.fromstring(svg)
    with Image.open(TEMPLATES_DIR / "white.png") as img:
        orig_w, orig_h = img.size
    view = [float(v) for v in root.get("viewBox").split()]
    width = view[2]
    height = view[3]
    assert width == orig_w * 0.5
    assert height == orig_h * 0.5
    assert root.get("width") == "1.5in"
    assert root.get("height").endswith("in")
    expected_height_in = 1.5 * (height / width)
    assert float(root.get("height")[:-2]) == pytest.approx(expected_height_in)


def test_apply_template_has_no_cut_line_border():
    inner = generate_svg("data")
    svg = apply_template(inner, "white.png")
    root = ET.fromstring(svg)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    border = [r for r in root.findall("svg:rect", ns) if r.get("stroke")]
    assert not border


def test_prepare_template_handles_svg(monkeypatch, tmp_path):
    monkeypatch.setattr(qr_module, "TEMPLATES_DIR", tmp_path)
    svg_path = tmp_path / "template.svg"
    svg_path.write_text(
        """
        <svg width="200" height="100" viewBox="0 0 200 100" xmlns="http://www.w3.org/2000/svg"></svg>
        """.strip()
    )
    tpl = qr_module.prepare_template("template.svg")
    assert tpl["data_uri"].startswith("data:image/svg+xml;base64,")
    assert tpl["width"] == pytest.approx(200.0)
    assert tpl["height"] == pytest.approx(100.0)


def test_apply_template_with_svg_background(monkeypatch, tmp_path):
    monkeypatch.setattr(qr_module, "TEMPLATES_DIR", tmp_path)
    svg_path = tmp_path / "background.svg"
    svg_path.write_text(
        """
        <svg width="150" height="250" viewBox="0 0 150 250" xmlns="http://www.w3.org/2000/svg">
            <rect width="150" height="250" fill="#ffffff" />
        </svg>
        """.strip()
    )
    inner = generate_svg("data")
    svg = apply_template(inner, svg_path.name)
    root = ET.fromstring(svg)
    images = root.findall("{http://www.w3.org/2000/svg}image")
    assert images, "Expected background image element"
    href = images[0].get("{http://www.w3.org/1999/xlink}href")
    assert href.startswith("data:image/svg+xml;base64,")
    view = [float(v) for v in root.get("viewBox").split()]
    assert view[2] == pytest.approx(150.0)
    assert view[3] == pytest.approx(250.0)


def test_svg_template_uses_viewbox_units(monkeypatch, tmp_path):
    monkeypatch.setattr(qr_module, "TEMPLATES_DIR", tmp_path)
    svg_path = tmp_path / "physical.svg"
    svg_path.write_text(
        """
        <svg width="6in" height="4in" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
            <rect width="600" height="400" fill="#ffffff" />
        </svg>
        """.strip()
    )

    tpl = qr_module.prepare_template(svg_path.name)
    assert tpl["width"] == pytest.approx(600.0)
    assert tpl["height"] == pytest.approx(400.0)

    inner = generate_svg("data")
    svg = apply_template(inner, svg_path.name)
    root = ET.fromstring(svg)
    view = [float(v) for v in root.get("viewBox").split()]
    assert view[2] == pytest.approx(600.0)
    assert view[3] == pytest.approx(400.0)

    inner_svg = root.find("{http://www.w3.org/2000/svg}svg")
    assert inner_svg is not None
    assert float(inner_svg.get("x")) == pytest.approx((600.0 - float(inner_svg.get("width"))) / 2)
    assert float(inner_svg.get("y")) == pytest.approx((400.0 - float(inner_svg.get("height"))) / 2)

def test_add_frame_sets_print_dimensions(monkeypatch):
    monkeypatch.setenv("QR_PRINT_WIDTH_IN", "3.5")
    svg = add_frame(generate_svg("data"))
    root = ET.fromstring(svg)
    assert root.get("width") == "3.5in"
    view = root.get("viewBox").split()
    outer_w = float(view[2])
    outer_h = float(view[3])
    expected_height = 3.5 * outer_h / outer_w
    assert abs(float(root.get("height")[:-2]) - expected_height) < 1e-6


def test_prepare_svg_variants_applies_filter_and_scaling(monkeypatch):
    monkeypatch.setenv("QR_PRINT_WIDTH_IN", "2.5")
    monkeypatch.setenv("QR_PREVIEW_SCALE", "0.5")
    base = add_frame(generate_svg("data"))
    final_svg, before_svg, after_svg = prepare_svg_variants(base, 0.3)

    ns = {"svg": "http://www.w3.org/2000/svg"}
    final_root = ET.fromstring(final_svg)
    defs = final_root.find("svg:defs", ns)
    assert defs is not None
    filt = defs.find("svg:filter", ns)
    assert filt is not None
    assert not filt.findall("svg:feMorphology", ns)
    assert not filt.findall("svg:feComposite", ns)
    sat_nodes = [
        node
        for node in filt.findall("svg:feColorMatrix", ns)
        if node.get("type") == "saturate"
    ]
    assert sat_nodes, "Expected saturate color matrix when saturation boost is set"

    before_root = ET.fromstring(before_svg)
    assert before_root.get("width").endswith("in")
    assert float(before_root.get("width")[:-2]) == pytest.approx(1.25)

    after_root = ET.fromstring(after_svg)
    group = after_root.find("svg:g", ns)
    assert group is not None and group.get("filter").startswith("url(#post_")


def test_prepare_svg_variants_saturation_only():
    base = add_frame(generate_svg("data"))
    final_svg, _, after_svg = prepare_svg_variants(base, 0.2)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    final_root = ET.fromstring(final_svg)
    defs = final_root.find("svg:defs", ns)
    assert defs is not None
    filt = defs.find("svg:filter", ns)
    assert filt is not None
    # Saturation-only filters should not create morphology or composite nodes
    assert not filt.findall("svg:feMorphology", ns)
    assert not filt.findall("svg:feComposite", ns)
    color_matrix = [
        node
        for node in filt.findall("svg:feColorMatrix", ns)
        if node.get("type") == "saturate"
    ]
    assert color_matrix, "Expected saturate color matrix"

    after_root = ET.fromstring(after_svg)
    group = after_root.find("svg:g", ns)
    assert group is not None


def test_prepare_svg_variants_no_changes_returns_original():
    base = add_frame(generate_svg("data"))
    final_svg, before_svg, after_svg = prepare_svg_variants(base, 0.0)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    final_root = ET.fromstring(final_svg)
    group = final_root.find("svg:g", ns)
    assert group is None or "filter" not in group.attrib
    assert before_svg != ""
    assert after_svg != ""
