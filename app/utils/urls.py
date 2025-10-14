"""Helpers for building user-facing URLs."""
from __future__ import annotations

import os


def build_location_display_path(location_id: int) -> str:
    """Return the relative path for the public location display page."""
    return f"/locations/{location_id}/display"


def build_location_display_url(location_id: int) -> str:
    """Return an absolute URL for the public location display page when possible."""
    base = os.environ.get("PUBLIC_HOST_URL", "").rstrip("/")
    path = build_location_display_path(location_id)
    if base:
        return f"{base}{path}"
    return path
