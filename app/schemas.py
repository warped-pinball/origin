from pydantic import BaseModel, ConfigDict, Field, field_validator
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
    name: Optional[str] = None


class MachineCreate(MachineBase):
    secret: str
    location_id: Optional[int] = None


class Machine(MachineBase):
    id: str
    user_id: Optional[int] = None
    location_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class OwnedMachine(BaseModel):
    id: str
    name: str
    game_title: str
    location_id: Optional[int] = None


class MachineResponse(BaseModel):
    signature: str


class MachineHandshakeRequest(BaseModel):
    """Payload sent by devices to initiate a handshake."""

    client_public_key_b64: str
    game_title: str


class MachineChallengesRequest(BaseModel):
    n: int = 1  # number of challenges to generate


class MachineHandshake(BaseModel):
    """Response returned to devices after a successful handshake."""

    machine_id: str
    server_key: str
    claim_code: str
    claim_url: str

    model_config = ConfigDict(from_attributes=True)


class MachineClaimStatus(BaseModel):
    is_claimed: bool = True
    claim_url: Optional[str] = None
    username: Optional[str] = None


class MachineGameStateCreate(BaseModel):
    game_time_ms: int = Field(..., alias="gameTimeMs", ge=0)
    ball_in_play: int = Field(..., alias="ballInPlay", ge=0)
    scores: list[int]
    player_up: Optional[int] = Field(default=None, alias="playerUp", ge=0)
    players_total: Optional[int] = Field(default=None, alias="playerCount", ge=0)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("scores")
    @classmethod
    def validate_scores(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("scores must contain at least one entry")
        return value


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
    display_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LocationMachineLink(BaseModel):
    machine_id: str


class ScoreboardScore(BaseModel):
    value: int
    achieved_at: datetime
    player_name: Optional[str] = None


class MachineScoreboard(BaseModel):
    machine_id: str
    game_title: Optional[str] = None
    is_active: bool
    updated_at: Optional[datetime] = None
    scores: list[int] = Field(default_factory=list)
    ball_in_play: Optional[int] = None
    player_up: Optional[int] = None
    players_total: Optional[int] = None
    high_scores: dict[str, list[ScoreboardScore]] = Field(default_factory=dict)


class LocationScoreboard(BaseModel):
    location_id: int
    location_name: str
    machines: list[MachineScoreboard]
    generated_at: datetime


class ScoreBase(BaseModel):
    game: str
    value: int


class ScoreCreate(ScoreBase):
    user_id: int
    machine_id: str


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
