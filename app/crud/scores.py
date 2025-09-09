from typing import List, Optional
from sqlalchemy.orm import Session
from .. import models, schemas


def create_score(db: Session, score: schemas.ScoreCreate) -> models.Score:
    db_score = models.Score(**score.dict())
    db.add(db_score)
    db.commit()
    db.refresh(db_score)
    return db_score


def get_top_scores(
    db: Session, game: str, limit: int = 10, offset: int = 0
) -> List[models.Score]:
    return (
        db.query(models.Score)
        .filter(models.Score.game == game)
        .order_by(models.Score.value.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_user_scores(
    db: Session,
    user_id: int,
    game: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    top: bool = False,
) -> List[models.Score]:
    query = db.query(models.Score).filter(models.Score.user_id == user_id)
    if game:
        query = query.filter(models.Score.game == game)
    order = models.Score.value.desc() if top else models.Score.created_at.desc()
    return query.order_by(order).offset(offset).limit(limit).all()
