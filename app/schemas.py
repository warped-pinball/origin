from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    screen_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    initials: Optional[str] = None
    profile_picture: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

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
