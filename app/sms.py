import os
import httpx
import logging

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")
API_BASE = os.getenv("PUBLIC_API_URL", "")

logger = logging.getLogger(__name__)


def is_sms_configured() -> bool:
    """Return True if all required Twilio settings are present."""
    return all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER])


def send_sms(to: str, body: str) -> None:
    """Send an SMS using Twilio if credentials are configured."""
    if not is_sms_configured():
        return
    data = {"To": to, "From": TWILIO_FROM_NUMBER, "Body": body}
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    try:
        httpx.post(url, data=data, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=10)
        logger.info("Sent SMS to %s", to)
    except Exception:
        logger.exception("Failed to send SMS to %s", to)


def send_verification_sms(phone: str, token: str) -> None:
    link = f"{API_BASE}/api/v1/auth/verify?token={token}"
    body = f"Verify your account: {link}"
    send_sms(phone, body)


def send_password_reset_sms(phone: str, token: str) -> None:
    link = f"{API_BASE}/reset-password?token={token}"
    body = f"Reset your password: {link}"
    send_sms(phone, body)

