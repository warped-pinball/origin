from sqlalchemy.orm import Session
from .. import models, schemas
from passlib.context import CryptContext
from typing import Optional
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the password matches the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_email(db: Session, email_addr: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email_addr).first()


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = pwd_context.hash(user.password)
    verification_token = secrets.token_urlsafe(32)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        screen_name=user.screen_name,
        verification_token=verification_token,
        is_verified=False,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email_addr: str, password: str) -> Optional[models.User]:
    user = get_user_by_email(db, email_addr)
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


def delete_user(db: Session, user: models.User) -> None:
    db.delete(user)
    db.commit()
