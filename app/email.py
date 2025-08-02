import os
import httpx
import logging

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER = os.getenv("BREVO_SENDER_EMAIL", "noreply@example.com")

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, text: str) -> None:
    """Send an email using Brevo if credentials are configured."""
    if not BREVO_API_KEY:
        return
    url = "https://api.brevo.com/v3/smtp/email"
    data = {
        "sender": {"email": BREVO_SENDER},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": text,
    }
    try:
        httpx.post(url, json=data, headers={"api-key": BREVO_API_KEY}, timeout=10)
        logger.info("Sent email to %s", to)
    except Exception:
        logger.exception("Failed to send email to %s", to)


def send_verification_email(email: str, token: str) -> None:
    host = os.getenv("PUBLIC_HOST_URL", "")
    link = f"{host}/api/v1/auth/verify?token={token}"
    
    # get template from email_templates directory
    email_templates_dir = os.path.join(os.path.dirname(__file__), "email_templates")
    with open(os.path.join(email_templates_dir, "verify_email.jinja"), "r") as file:
        template = file.read()
        text = template.format(link=link)
   
    send_email(email, "Verify your Warped Pinball account", text)


def send_password_reset_email(email: str, token: str) -> None:
    host = os.getenv("PUBLIC_HOST_URL", "")
    link = f"{host}/reset-password?token={token}"
    text = f"Reset your password: {link}"
    send_email(email, "Reset your password", text)

