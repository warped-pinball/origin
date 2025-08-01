from pathlib import Path
import gzip

from scripts import build_static


def test_minifiers_and_gzip(tmp_path: Path):
    # JavaScript using terser
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
