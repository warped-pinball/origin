from pathlib import Path


from scripts import build_static


def test_minify_js_app_creates_min_file(tmp_path: Path):
    app_js = tmp_path / "app.js"
    app_js.write_text("function add(a, b) { return a + b; }")
    min_js = build_static.minify_js(app_js)
    assert min_js.name == "app.min.js"
    assert min_js.exists()
    assert len(min_js.read_text()) < len("function add(a, b) { return a + b; }")

