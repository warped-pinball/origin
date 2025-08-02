from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext
from typing import List, Optional
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the password matches the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

# Users

def get_user_by_phone(db: Session, phone: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.phone == phone).first()

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = pwd_context.hash(user.password)
    verification_token = secrets.token_urlsafe(32)
    db_user = models.User(
        phone=user.phone,
        hashed_password=hashed_password,
        screen_name=user.screen_name,
        verification_token=verification_token,
        is_verified=False,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, phone: str, password: str) -> Optional[models.User]:
    user = get_user_by_phone(db, phone)
    if not user:
        return None
    if not pwd_context.verify(password, user.hashed_password):
        return None
    return user

def update_user(db: Session, user: models.User, updates: schemas.UserUpdate) -> models.User:
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user_password(db: Session, user: models.User, password: str) -> models.User:
    user.hashed_password = pwd_context.hash(password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def verify_user(db: Session, token: str) -> Optional[models.User]:
    user = db.query(models.User).filter(models.User.verification_token == token).first()
    if not user:
        return None
    user.is_verified = True
    user.verification_token = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_reset_token(db: Session, user: models.User) -> str:
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    db.add(user)
    db.commit()
    return token


def reset_password(db: Session, token: str, password: str) -> Optional[models.User]:
    user = db.query(models.User).filter(models.User.reset_token == token).first()
    if not user:
        return None
    user.hashed_password = pwd_context.hash(password)
    user.reset_token = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user: models.User):
    db.delete(user)
    db.commit()

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
