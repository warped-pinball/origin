import os
import base64
import logging
from functools import lru_cache
from io import BytesIO

import httpx
from PIL import Image
from jinja2 import Environment, FileSystemLoader

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER = os.getenv("BREVO_SENDER_EMAIL", "noreply@example.com")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "email_templates")
template_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=False)

logger = logging.getLogger(__name__)


@lru_cache()
def _logo_data_uri() -> str:
    """Return the logo image as a data URI with transparent pixels filled white."""
    path = os.path.join(os.path.dirname(__file__), "static", "img", "logo.png")
    with Image.open(path) as img:
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            background = Image.new("RGBA", img.size, "white")
            background.paste(img, mask=img.getchannel("A"))
            img = background
        buffer = BytesIO()
        img.convert("RGB").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    """Send an email using Brevo if credentials are configured."""
    if not BREVO_API_KEY:
        return
    url = "https://api.brevo.com/v3/smtp/email"
    data = {
        "sender": {"email": BREVO_SENDER},
        "to": [{"email": to}],
        "subject": subject,
    }
    if text:
        data["textContent"] = text
    if html:
        data["htmlContent"] = html
    try:
        httpx.post(url, json=data, headers={"api-key": BREVO_API_KEY}, timeout=10)
        logger.info("Sent email to %s", to)
    except Exception:
        logger.exception("Failed to send email to %s", to)


def _render_template(name: str, **context: str) -> str:
    template = template_env.get_template(name)
    return template.render(**context)


def _send_action_email(
    email: str,
    screen_name: str,
    subject: str,
    message: str,
    action_url: str,
    action_text: str,
) -> None:
    logo_url = _logo_data_uri()
    text = _render_template(
        "action_email.jinja",
        screen_name=screen_name,
        message=message,
        action_url=action_url,
        action_text=action_text,
    )
    html = _render_template(
        "action_email.html.jinja",
        screen_name=screen_name,
        message=message,
        action_url=action_url,
        action_text=action_text,
        logo_url=logo_url,
    )
    send_email(email, subject, text, html)


def send_verification_email(email: str, screen_name: str, token: str) -> None:
    host = os.getenv("PUBLIC_HOST_URL", "")
    link = f"{host}/api/v1/auth/verify?token={token}"
    _send_action_email(
        email,
        screen_name,
        "Verify your Warped Pinball account",
        "Please verify your email to finish creating your account.",
        link,
        "Verify your account",
    )


def send_password_reset_email(email: str, screen_name: str, token: str) -> None:
    host = os.getenv("PUBLIC_HOST_URL", "")
    link = f"{host}/reset-password?token={token}"
    _send_action_email(
        email,
        screen_name,
        "Reset your password",
        "Use the link below to reset your password. If you didn't request this, you can ignore this email.",
        link,
        "Reset your password",
    )

