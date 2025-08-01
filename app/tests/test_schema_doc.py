from scripts.generate_schema_md import generate_schema_md, DOC_PATH


def test_schema_documentation_up_to_date():
    generated = generate_schema_md().strip()
    existing = DOC_PATH.read_text().strip()
    assert existing == generated
