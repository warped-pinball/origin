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
