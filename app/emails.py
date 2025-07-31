import os
import httpx

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "no-reply@example.com")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "Origin")
API_BASE = os.getenv("PUBLIC_API_URL", "")


def send_email(to: str, subject: str, html: str) -> None:
    if not BREVO_API_KEY:
        # Skip sending if API key is not provided
        return
    data = {
        "sender": {"email": BREVO_SENDER_EMAIL, "name": BREVO_SENDER_NAME},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html,
    }
    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        "accept": "application/json",
    }
    try:
        httpx.post(
            "https://api.brevo.com/v3/smtp/email", json=data, headers=headers, timeout=10
        )
    except Exception:
        pass


def send_verification_email(email: str, token: str) -> None:
    link = f"{API_BASE}/api/v1/auth/verify?token={token}"
    html = f"<p>Please verify your email by clicking <a href='{link}'>here</a>.</p>"
    send_email(email, "Verify your email", html)


def send_password_reset_email(email: str, token: str) -> None:
    link = f"{API_BASE}/reset-password?token={token}"
    html = f"<p>Reset your password by clicking <a href='{link}'>here</a>.</p>"
    send_email(email, "Reset your password", html)
