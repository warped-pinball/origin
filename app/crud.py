from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext
from typing import List, Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Users

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password,
                          name=user.name, initials=user.initials,
                          profile_picture=user.profile_picture)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not pwd_context.verify(password, user.hashed_password):
        return None
    return user

# Machines

def create_machine(db: Session, machine: schemas.MachineCreate) -> models.Machine:
    db_machine = models.Machine(name=machine.name, secret=machine.secret)
    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)
    return db_machine

def get_machine(db: Session, machine_id: int) -> Optional[models.Machine]:
    return db.query(models.Machine).filter(models.Machine.id == machine_id).first()

def get_machine_by_name(db: Session, name: str) -> Optional[models.Machine]:
    return db.query(models.Machine).filter(models.Machine.name == name).first()

# Scores

def create_score(db: Session, score: schemas.ScoreCreate) -> models.Score:
    db_score = models.Score(**score.dict())
    db.add(db_score)
    db.commit()
    db.refresh(db_score)
    return db_score

def get_top_scores(db: Session, game: str, limit: int = 10, offset: int = 0) -> List[models.Score]:
    return (db.query(models.Score)
            .filter(models.Score.game == game)
            .order_by(models.Score.value.desc())
            .offset(offset)
            .limit(limit)
            .all())

def get_user_scores(db: Session, user_id: int, game: Optional[str] = None,
                    limit: int = 10, offset: int = 0, top: bool = False) -> List[models.Score]:
    query = db.query(models.Score).filter(models.Score.user_id == user_id)
    if game:
        query = query.filter(models.Score.game == game)
    order = models.Score.value.desc() if top else models.Score.created_at.desc()
    return query.order_by(order).offset(offset).limit(limit).all()
