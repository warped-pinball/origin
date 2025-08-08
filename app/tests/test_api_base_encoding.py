import json
from app.main import templates

MALICIOUS = '/foo";alert(1);//'


def render(template_name: str) -> str:
    template = templates.get_template(template_name)
    return template.render(api_base=MALICIOUS, version='test')


def assert_api_base_encoded(rendered: str) -> None:
    expected = f'window.API_BASE = {json.dumps(MALICIOUS)};'
    assert expected in rendered
    unexpected = f'window.API_BASE = "{MALICIOUS}";'
    assert unexpected not in rendered


def test_index_api_base_encoded():
    html = render('index.html')
    assert_api_base_encoded(html)


def test_signup_api_base_encoded():
    html = render('signup.html')
    assert_api_base_encoded(html)


def test_reset_password_api_base_encoded():
    html = render('reset_password.html')
    assert_api_base_encoded(html)
