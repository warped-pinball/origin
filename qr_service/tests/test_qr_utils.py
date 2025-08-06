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

def test_add_frame_removes_namespace_prefixes():
    inner = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300"></svg>'
    framed = add_frame(inner)
    assert 'ns0:' not in framed
