from pathlib import Path


from scripts import build_static


def test_minify_js_app_creates_min_file(tmp_path: Path):
    app_js = tmp_path / "app.js"
    app_js.write_text("function add(a, b) { return a + b; }")
    min_js = build_static.minify_js(app_js)
    assert min_js.name == "app.min.js"
    assert min_js.exists()
    assert len(min_js.read_text()) < len("function add(a, b) { return a + b; }")


def test_minify_service_worker_keeps_name(tmp_path: Path):
    sw_js = tmp_path / "service-worker.js"
    sw_js.write_text("self.addEventListener('install', () => {});")
    min_js = build_static.minify_js(sw_js)
    assert min_js.name == "service-worker.js"
    assert min_js.exists()
    assert len(min_js.read_text()) < len("self.addEventListener('install', () => {});")

