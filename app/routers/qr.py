import os
from base64 import urlsafe_b64decode
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud, models
from ..auth import get_current_user, get_current_user_optional
from ..database import get_db

router = APIRouter(tags=["qr"])
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


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
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional),
):
    if not current_user:
        next_url = quote(f"/q?r={r}", safe="")
        return RedirectResponse(f"/?next={next_url}", status_code=status.HTTP_302_FOUND)
    qr_id = _decode_id(r)
    qr = db.query(models.QRCode).filter(models.QRCode.id == qr_id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR code not found")
    host = os.environ.get("PUBLIC_HOST_URL", "")
    if qr.machine_id:
        location = f"{host}/machines/{qr.machine_id}"
        return RedirectResponse(location, status_code=status.HTTP_302_FOUND)

    machines = crud.get_machines_for_user(db, current_user.id)
    return templates.TemplateResponse(
        "assign_qr.html",
        {"request": request, "code": r, "machines": machines},
    )


@router.post("/q/assign")
def assign_qr(
    code: str = Form(...),
    machine_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    qr_id = _decode_id(code)
    qr = (
        db.query(models.QRCode)
        .filter(models.QRCode.id == qr_id, models.QRCode.user_id == current_user.id)
        .first()
    )
    if not qr:
        raise HTTPException(status_code=404, detail="QR code not found")
    machine = (
        db.query(models.Machine)
        .filter(
            models.Machine.id == machine_id, models.Machine.user_id == current_user.id
        )
        .first()
    )
    if not machine:
        raise HTTPException(status_code=400, detail="Invalid machine")
    qr.machine_id = machine_id
    db.add(qr)
    db.commit()
    host = os.environ.get("PUBLIC_HOST_URL", "")
    location = f"{host}/machines/{machine_id}"
    return RedirectResponse(location, status_code=status.HTTP_302_FOUND)
