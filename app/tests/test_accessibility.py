from pathlib import Path
import re


def _read(name: str) -> str:
    return (Path(__file__).resolve().parent.parent / "templates" / name).read_text()


def test_login_form_labels():
    content = _read("index.html")
    assert re.search(r"<label for=['\"]login-email['\"]>", content)
    assert re.search(r"<label for=['\"]login-password['\"]>", content)


def test_login_form_autocomplete():
    content = _read("index.html")
    assert re.search(r"id=['\"]login-email['\"][^>]*autocomplete=['\"]username['\"]", content)
    assert re.search(r"id=['\"]login-password['\"][^>]*autocomplete=['\"]current-password['\"]", content)
    assert re.search(r"id=['\"]account-password['\"][^>]*autocomplete=['\"]new-password['\"]", content)


def test_signup_form_labels():
    content = _read("signup.html")
    assert re.search(r"<label for=['\"]signup-email['\"]>", content)
    assert re.search(r"<label for=['\"]signup-screen['\"]>", content)
    assert re.search(r"<label for=['\"]signup-password['\"]>", content)


def test_signup_autocomplete_attributes():
    content = _read("signup.html")
    assert re.search(r"id=['\"]signup-email['\"][^>]*autocomplete=['\"]email['\"]", content)
    assert re.search(r"id=['\"]signup-password['\"][^>]*autocomplete=['\"]new-password['\"]", content)


def test_reset_password_labels():
    content = _read("reset_password.html")
    assert re.search(r"<label for=['\"]reset-email['\"]>", content)
    assert re.search(r"<label for=['\"]new-password['\"]>", content)


def test_reset_password_autocomplete():
    content = _read("reset_password.html")
    assert re.search(r"id=['\"]reset-email['\"][^>]*autocomplete=['\"]email['\"]", content)
    assert re.search(r"id=['\"]new-password['\"][^>]*autocomplete=['\"]new-password['\"]", content)


def test_nav_links_have_titles():
    content = _read("index.html")
    for page, title in [
        ("achievements", "Achievements"),
        ("tournaments", "Tournaments"),
        ("friends", "Friends"),
        ("settings", "Settings"),
    ]:
        pattern = rf"data-page=['\"]{page}['\"]([^>]*?)title=['\"]{title}['\"]"
        assert re.search(pattern, content)
