from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/scores", tags=["scores"])

@router.post("/", response_model=schemas.Score)
def submit_score(
    score: schemas.ScoreCreate,
    db: Session = Depends(get_db),
    current_user: crud.models.User = Depends(get_current_user),
):
    return crud.create_score(db, score, user_id=current_user.id)

@router.get("/top/{game}", response_model=List[schemas.ScoreOut])
def get_top_scores(game: str, limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
    scores = crud.get_top_scores(db, game, limit, offset)
    return scores

@router.get("/user/{user_id}", response_model=List[schemas.ScoreOut])
def get_user_scores(user_id: int, game: Optional[str] = None, limit: int = 10, offset: int = 0, top: bool = False, db: Session = Depends(get_db)):
    scores = crud.get_user_scores(db, user_id, game, limit, offset, top)
    return scores
