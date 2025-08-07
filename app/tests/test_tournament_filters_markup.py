from pathlib import Path


def test_tournament_filter_buttons_group():
    index_html = Path(__file__).resolve().parent.parent / "templates" / "index.html"
    content = index_html.read_text()
    line = next((l for l in content.splitlines() if "tournament-filter-buttons" in l), None)
    assert line is not None, "tournament-filter-buttons div missing"
    assert "role='group'" in line or 'role="group"' in line
