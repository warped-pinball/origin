from pathlib import Path
import gzip

import rjsmin

from scripts import build_static


def test_minifiers_and_gzip(tmp_path: Path):
    # JavaScript
    js = tmp_path / "test.js"
    js.write_text("function add(a, b) { return a + b; }")
    min_js = build_static.minify_js(js)
    assert min_js.exists()
    assert len(min_js.read_text()) < len("function add(a, b) { return a + b; }")
    gz_js = build_static.gzip_file(min_js)
    with gzip.open(gz_js, "rt") as f:
        assert f.read() == min_js.read_text()

    # CSS
    css = tmp_path / "style.css"
    css.write_text("body { color: red; }")
    build_static.minify_css(css)
    assert css.read_text() == "body{color:red}"
    gz_css = build_static.gzip_file(css)
    with gzip.open(gz_css, "rt") as f:
        assert f.read() == css.read_text()

    # HTML
    html = tmp_path / "index.html"
    html.write_text("<html>\n  <body> Test </body>\n</html>")
    build_static.minify_html(html)
    assert "\n" not in html.read_text()
    gz_html = build_static.gzip_file(html)
    with gzip.open(gz_html, "rt") as f:
        assert f.read() == html.read_text()

    # JSON
    jsn = tmp_path / "data.json"
    jsn.write_text('{\n "a": 1\n}')
    build_static.minify_json_file(jsn)
    assert jsn.read_text() == '{"a":1}'
    gz_json = build_static.gzip_file(jsn)
    with gzip.open(gz_json, "rt") as f:
        assert f.read() == jsn.read_text()


def test_minify_js_app_creates_min_file(tmp_path: Path):
    app_js = tmp_path / "app.js"
    app_js.write_text("function add(a, b) { return a + b; }")
    min_js = build_static.minify_js(app_js)
    assert min_js.name == "app.min.js"
    assert min_js.exists()
    assert len(min_js.read_text()) < len("function add(a, b) { return a + b; }")


def test_build_outputs_only_to_build_dir(tmp_path: Path):
    src = tmp_path / "static"
    js_dir = src / "js"
    js_dir.mkdir(parents=True)
    original = "function add(a, b) { return a + b; }"
    (js_dir / "app.js").write_text(original)
    build_dir = tmp_path / "build"

    build_static.build_static(src, build_dir)

    # Source directory should remain unchanged
    assert sorted(p.name for p in js_dir.iterdir()) == ["app.js"]
    assert (js_dir / "app.js").read_text() == original

    # Build directory should contain minified and gzipped assets
    built_js_dir = build_dir / "js"
    min_path = built_js_dir / "app.min.js"
    assert min_path.read_text() == rjsmin.jsmin(original)
    with gzip.open(min_path.with_suffix(".js.gz"), "rt") as f:
        assert f.read() == min_path.read_text()
