from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from .. import crud, schemas
from ..database import get_db
from ..auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from ..sms import send_password_reset_sms

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    phone = form_data.username.strip()
    user = crud.get_user_by_phone(db, phone)
    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid phone or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Phone not verified")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.phone}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/verify")
def verify_phone(token: str, db: Session = Depends(get_db)):
    user = crud.verify_user(db, token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"detail": "Phone verified"}


@router.post("/password-reset/request")
def request_password_reset(req: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_phone(db, req.phone)
    if user:
        token = crud.create_reset_token(db, user)
        send_password_reset_sms(user.phone, token)
    # Always return success to avoid leaking which phones exist
    return {"detail": "If the phone number exists, a reset link has been sent"}


@router.post("/password-reset/confirm")
def reset_password(data: schemas.PasswordReset, db: Session = Depends(get_db)):
    user = crud.reset_password(db, data.token, data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"detail": "Password updated"}
