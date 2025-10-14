from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..crud.dashboard import build_location_scoreboard
from ..database import get_db

router = APIRouter(prefix="/api/v1/public", tags=["public"])


@router.get("/locations/{location_id}/scoreboard", response_model=schemas.LocationScoreboard)
def get_location_scoreboard(location_id: int, db: Session = Depends(get_db)):
    data = build_location_scoreboard(db, location_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return data
