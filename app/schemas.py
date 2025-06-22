from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    initials: Optional[str] = None
    profile_picture: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        orm_mode = True

class MachineBase(BaseModel):
    name: str

class MachineCreate(MachineBase):
    secret: str

class Machine(MachineBase):
    id: int

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True

class ScoreOut(BaseModel):
    id: int
    value: int
    created_at: datetime
    user: User

    class Config:
        orm_mode = True
