from scripts.generate_schema_md import generate_schema_md


def test_schema_doc_includes_flyway_tables():
    content = generate_schema_md()
    assert "## users" in content
    assert "## qr_codes" in content

