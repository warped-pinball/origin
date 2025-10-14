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


def _try_decode_id(encoded: str) -> int | None:
    padding = "=" * (-len(encoded) % 4)
    try:
        decoded = urlsafe_b64decode(encoded + padding).decode()
    except Exception:
        return None
    try:
        return int(decoded)
    except ValueError:
        return None


def _build_qr_url(request: Request, code: str) -> str:
    host = os.environ.get("PUBLIC_HOST_URL", "").rstrip("/")
    if host:
        return f"{host}/q?r={code}"
    base = str(request.base_url).rstrip("/")
    return f"{base}/q?r={code}"


def _get_or_create_qr(
    db: Session,
    request: Request,
    code: str,
    *,
    create_missing: bool,
) -> models.QRCode:
    target_url = _build_qr_url(request, code)

    qr = (
        db.query(models.QRCode)
        .filter(models.QRCode.nfc_link == code)
        .first()
    )
    if qr:
        return qr

    qr = (
        db.query(models.QRCode)
        .filter(models.QRCode.url == target_url)
        .first()
    )
    if qr:
        if qr.nfc_link is None:
            qr.nfc_link = code
            db.add(qr)
            db.commit()
            db.refresh(qr)
        return qr

    qr = (
        db.query(models.QRCode)
        .filter(models.QRCode.url.like(f"%r={code}"))
        .first()
    )
    if qr:
        if qr.nfc_link is None:
            qr.nfc_link = code
            db.add(qr)
            db.commit()
            db.refresh(qr)
        return qr

    qr_id = _try_decode_id(code)
    if qr_id is not None:
        qr = (
            db.query(models.QRCode)
            .filter(models.QRCode.id == qr_id)
            .first()
        )
        if qr:
            if qr.nfc_link is None:
                qr.nfc_link = code
                db.add(qr)
                db.commit()
                db.refresh(qr)
            return qr

    if not create_missing:
        raise HTTPException(status_code=404, detail="QR code not found")

    qr = models.QRCode(url=target_url, nfc_link=code)
    db.add(qr)
    db.commit()
    db.refresh(qr)
    return qr


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
    qr = _get_or_create_qr(db, request, r, create_missing=True)

    host = os.environ.get("PUBLIC_HOST_URL", "")
    if qr.machine_id:
        location = f"{host}/machines/{qr.machine_id}"
        return RedirectResponse(location, status_code=status.HTTP_302_FOUND)

    if qr.user_id is None:
        qr.user_id = current_user.id
        db.add(qr)
        db.commit()
        db.refresh(qr)
    elif qr.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="QR code not found")

    machines = crud.get_machines_for_user(db, current_user.id)
    return templates.TemplateResponse(
        "assign_qr.html",
        {"request": request, "code": r, "machines": machines},
    )


@router.post("/q/assign")
def assign_qr(
    request: Request,
    code: str = Form(...),
    machine_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    qr = _get_or_create_qr(db, request, code, create_missing=False)
    if qr.user_id is None:
        qr.user_id = current_user.id
    elif qr.user_id != current_user.id:
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
