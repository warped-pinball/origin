import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .. import crud, models
from ..version import __version__
from ..database import get_db

router = APIRouter(include_in_schema=False)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
API_BASE = os.environ.get("PUBLIC_API_URL", "")


def _render(template_name: str):
    async def render(request: Request):
        return templates.TemplateResponse(
            request, template_name, {"version": __version__, "api_base": API_BASE}
        )

    return render


PAGE_TEMPLATES = {
    "/": "index.html",
    "/signup": "signup.html",
    "/signup/success": "signup_success.html",
    "/reset-password": "reset_password.html",
    "/privacy": "privacy.html",
    "/terms": "terms.html",
}

for path, template in PAGE_TEMPLATES.items():
    router.get(path, response_class=HTMLResponse)(_render(template))


@router.get("/machines/{machine_id}", response_class=HTMLResponse)
async def machine_portal(
    request: Request, machine_id: str, db: Session = Depends(get_db)
):
    machine = crud.get_machine(db, machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    location_name = machine.location.name if machine.location else None
    qr_links = [
        qr.url
        for qr in db.query(models.QRCode)
        .filter(models.QRCode.machine_id == machine.id)
        .order_by(models.QRCode.created_at.asc())
        .all()
    ]
    config = {
        "id": machine.id,
        "game_title": machine.game_title or machine.id,
        "location_name": location_name,
        "qr_links": qr_links,
    }

    return templates.TemplateResponse(
        request,
        "machine_detail.html",
        {
            "version": __version__,
            "api_base": API_BASE,
            "machine": machine,
            "machine_config": config,
        },
    )


@router.get("/locations/{location_id}/display", response_class=HTMLResponse)
async def location_display(
    request: Request,
    location_id: int,
    db: Session = Depends(get_db),
):
    location = crud.get_location(db, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")

    return templates.TemplateResponse(
        request,
        "location_display.html",
        {
            "version": __version__,
            "api_base": API_BASE,
            "location_id": location_id,
            "location_name": location.name,
        },
    )
