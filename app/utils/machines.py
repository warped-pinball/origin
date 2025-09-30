"""Utility helpers for working with machine records."""

import secrets
import string


def generate_claim_code(length: int = 8) -> str:
    """Generate a random alphanumeric claim code."""

    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


__all__ = ["generate_claim_code"]
