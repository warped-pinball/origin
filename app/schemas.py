from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    screen_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    screen_name: Optional[str] = None


class PasswordUpdate(BaseModel):
    password: str

class User(UserBase):
    id: int
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    password: str

class MachineBase(BaseModel):
    name: str

class MachineCreate(MachineBase):
    secret: str

class Machine(MachineBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class ScoreBase(BaseModel):
    game: str
    value: int

class ScoreCreate(ScoreBase):
    user_id: int
    machine_id: int

class Score(ScoreBase):
    id: int
    created_at: datetime
    user: User
    machine: Machine

    model_config = ConfigDict(from_attributes=True)

class ScoreOut(BaseModel):
    id: int
    value: int
    created_at: datetime
    user: User

    model_config = ConfigDict(from_attributes=True)
