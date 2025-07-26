from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import crud, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user)

@router.get("/me", response_model=schemas.User)
def read_users_me(current_user: crud.models.User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=schemas.User)
def update_me(updates: schemas.UserUpdate,
              db: Session = Depends(get_db),
              current_user: crud.models.User = Depends(get_current_user)):
    return crud.update_user(db, current_user, updates)


@router.post("/me/password", response_model=schemas.User)
def change_password(password_update: schemas.PasswordUpdate,
                    db: Session = Depends(get_db),
                    current_user: crud.models.User = Depends(get_current_user)):
    return crud.update_user_password(db, current_user, password_update.password)


@router.delete("/me")
def delete_me(db: Session = Depends(get_db),
              current_user: crud.models.User = Depends(get_current_user)):
    crud.delete_user(db, current_user)
    return {"detail": "Account deleted"}
