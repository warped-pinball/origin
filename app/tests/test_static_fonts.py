from pathlib import Path


def test_material_font_references():
    root = Path(__file__).resolve().parents[2]
    font_file = root / "app/static/fonts/MaterialSymbols.ttf"
    assert font_file.exists()

    css_dir = root / "app/static/css"
    expected = "src: url('../fonts/MaterialSymbols.ttf') format('truetype');"
    for css_name in ["material-icons.css", "material-symbols.css"]:
        css_path = css_dir / css_name
        content = css_path.read_text()
        assert expected in content
