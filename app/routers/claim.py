import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from .. import models, schemas

router = APIRouter(tags=["claim"])

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


@router.get("/claim", response_class=HTMLResponse)
def claim_page(request: Request, code: str, db: Session = Depends(get_db)):
    machine = (
        db.query(models.Machine)
        .filter(models.Machine.claim_code == code)
        .first()
    )
    if not machine or machine.user_id is not None:
        raise HTTPException(status_code=404, detail="Invalid claim code")
    return templates.TemplateResponse(
        request,
        "claim.html",
        {
            "code": code,
            "machine_id": machine.id,
            "game_title": machine.game_title,
        },
    )


class ClaimRequest(schemas.BaseModel):
    code: str


@router.post("/api/claim", status_code=204)
def finalize_claim(
    req: ClaimRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    machine = (
        db.query(models.Machine)
        .filter(models.Machine.claim_code == req.code)
        .first()
    )
    if not machine:
        raise HTTPException(status_code=404, detail="Code not found")
    if machine.user_id is not None:
        raise HTTPException(status_code=409, detail="Code already claimed")
    machine.user_id = current_user.id
    machine.claim_code = None
    db.commit()
    return Response(status_code=204)


# @router.get("/api/machines/{machine_id}/status")
# def machine_status(machine_id: str, db: Session = Depends(get_db)):
#     machine = db.query(models.Machine).filter_by(id=machine_id).first()
#     return {"linked": bool(machine and machine.user_id)}
