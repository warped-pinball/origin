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
    claim = (
        db.query(models.MachineClaim)
        .filter(models.MachineClaim.claim_code == code)
        .first()
    )
    if not claim or claim.claimed:
        raise HTTPException(status_code=404, detail="Invalid claim code")
    return templates.TemplateResponse(
        request,
        "claim.html",
        {
            "code": code,
            "machine_id": claim.machine_id,
            "game_title": claim.client_game_title,
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
    claim = (
        db.query(models.MachineClaim)
        .filter(models.MachineClaim.claim_code == req.code)
        .first()
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Code not found")
    if claim.claimed:
        raise HTTPException(status_code=409, detail="Code already claimed")
    claim.user_id = current_user.id
    claim.claimed = True
    claim.claim_code = None
    db.commit()
    return Response(status_code=204)


# @router.get("/api/machines/{machine_id}/status")
# def machine_status(machine_id: str, db: Session = Depends(get_db)):
#     claim = db.query(models.MachineClaim).filter_by(machine_id=machine_id).first()
#     return {"linked": bool(claim and claim.claimed)}
