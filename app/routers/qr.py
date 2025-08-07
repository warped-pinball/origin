import os
from base64 import urlsafe_b64decode
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user_optional
from .. import models

router = APIRouter(tags=["qr"])


def _decode_id(encoded: str) -> int:
    padding = "=" * (-len(encoded) % 4)
    try:
        decoded = urlsafe_b64decode(encoded + padding).decode()
        return int(decoded)
    except Exception as exc:  # pragma: no cover - error path
        raise HTTPException(status_code=400, detail="Invalid code") from exc


@router.get("/q")
def handle_qr(
    r: str,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional),
):
    if not current_user:
        next_url = quote(f"/q?r={r}", safe="")
        return RedirectResponse(f"/?next={next_url}")
    qr_id = _decode_id(r)
    qr = db.query(models.QRCode).filter(models.QRCode.id == qr_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR code not found")
    host = os.environ.get("PUBLIC_HOST_URL", "")
    if qr.machine_id:
        location = f"{host}/machines/{qr.machine_id}"
    else:
        location = f"{host}/machines/assign?code={r}"
    return RedirectResponse(location)
