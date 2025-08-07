import os
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
        '<img src="https://example.com/static/img/logo.png"' in captured["html"]
    )
    assert 'style="display:inline-block' in captured["html"]


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
        '<img src="https://example.com/static/img/logo.png"' in captured["html"]
    )
    assert 'style="display:inline-block' in captured["html"]
