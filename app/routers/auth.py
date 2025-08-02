from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from .. import crud, schemas
from ..database import get_db
from ..auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from ..email import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    email = form_data.username.strip()
    user = crud.get_user_by_email(db, email)
    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = crud.verify_user(db, token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"detail": "Email verified"}


@router.post("/password-reset/request")
def request_password_reset(req: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, req.email)
    if user:
        token = crud.create_reset_token(db, user)
        send_password_reset_email(user.email, user.screen_name, token)
    # Always return success to avoid leaking which emails exist
    return {"detail": "If the email exists, a reset link has been sent"}


@router.post("/password-reset/confirm")
def reset_password(data: schemas.PasswordReset, db: Session = Depends(get_db)):
    user = crud.reset_password(db, data.token, data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"detail": "Password updated"}
