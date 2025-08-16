import os
import re
import base64
from io import BytesIO
from PIL import Image
from app import email


def test_verification_email_link(monkeypatch):
    os.environ["PUBLIC_HOST_URL"] = "https://example.com"
    captured = {}

    def fake_send_email(to, subject, text, html):
        captured["to"] = to
        captured["subject"] = subject
        captured["text"] = text
        captured["html"] = html

    monkeypatch.setattr(email, "send_email", fake_send_email)
    email.send_verification_email("user@example.com", "Screen", "tok")
    assert "Hello Screen" in captured["text"]
    assert (
        "Verify your account: https://example.com/api/v1/auth/verify?token=tok"
        in captured["text"]
    )
    assert (
        '<a href="https://example.com/api/v1/auth/verify?token=tok"'
        in captured["html"]
    )
    assert "Verify your account" in captured["html"]
    assert (
        'src="data:image/png;base64' in captured["html"]
    )
    _assert_logo_has_no_transparency(captured["html"])
    assert 'style="display:inline-block' in captured["html"]
    assert '@media (prefers-color-scheme: dark)' in captured["html"]
    assert 'class="logo"' in captured["html"]


def test_password_reset_email_link(monkeypatch):
    os.environ["PUBLIC_HOST_URL"] = "https://example.com"
    captured = {}

    def fake_send_email(to, subject, text, html):
        captured["to"] = to
        captured["subject"] = subject
        captured["text"] = text
        captured["html"] = html

    monkeypatch.setattr(email, "send_email", fake_send_email)
    email.send_password_reset_email("user@example.com", "Screen", "tok")
    assert "Hello Screen" in captured["text"]
    assert "If you didn't request this, you can ignore this email." in captured["text"]
    assert (
        "Reset your password: https://example.com/reset-password?token=tok"
        in captured["text"]
    )
    assert (
        '<a href="https://example.com/reset-password?token=tok"'
        in captured["html"]
    )
    assert "Reset your password" in captured["html"]
    assert "If you didn't request this" in captured["html"]
    assert (
        'src="data:image/png;base64' in captured["html"]
    )
    _assert_logo_has_no_transparency(captured["html"])
    assert 'style="display:inline-block' in captured["html"]
    assert '@media (prefers-color-scheme: dark)' in captured["html"]
    assert 'class="logo"' in captured["html"]


def _assert_logo_has_no_transparency(html: str) -> None:
    match = re.search(r'src="data:image/png;base64,([^"]+)"', html)
    assert match, "Logo data URI not found"
    data = base64.b64decode(match.group(1))
    img = Image.open(BytesIO(data))
    assert img.mode == "RGB"
