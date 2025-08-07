from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserBase(BaseModel):
    email: str
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
    email: str


class PasswordReset(BaseModel):
    token: str
    password: str

class MachineBase(BaseModel):
    name: str

class MachineCreate(MachineBase):
    secret: str

    location_id: Optional[int] = None


class Machine(MachineBase):
    id: int
    user_id: Optional[int] = None
    location_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class LocationBase(BaseModel):
    name: str
    address: Optional[str] = None
    website: Optional[str] = None
    hours: Optional[str] = None


class LocationCreate(LocationBase):
    pass


class Location(LocationBase):
    id: int
    machines: list[Machine] = []

    model_config = ConfigDict(from_attributes=True)


class LocationMachineLink(BaseModel):
    machine_id: int

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
