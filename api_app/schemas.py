from __future__ import annotations

import re
from typing import Optional, List, Dict, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator
from datetime import datetime

ALLOWED_INITIALS_PATTERN = re.compile(r"^[A-Z0-9]{3}$")


class MachineBase(BaseModel):
    name: str
    ip_address: str
    uid: str
    version: Optional[str] = None
    version_checked_at: Optional[datetime] = None

class MachineCreate(MachineBase):
    pass

class Machine(MachineBase):
    id: int
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)

class PlayerBase(BaseModel):
    initials: str
    screen_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    phone_number: Optional[str] = None

    @field_validator("initials")
    @classmethod
    def validate_initials(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not ALLOWED_INITIALS_PATTERN.fullmatch(normalized):
            raise ValueError("Initials must be exactly 3 capital letters or numbers.")
        return normalized

    @field_validator("screen_name")
    @classmethod
    def validate_screen_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Screen name cannot be empty.")
        return cleaned

class PlayerCreate(PlayerBase):
    pass

class PlayerUpdate(BaseModel):
    initials: Optional[str] = None
    screen_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None

    @field_validator("initials")
    @classmethod
    def validate_initials(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().upper()
        if not ALLOWED_INITIALS_PATTERN.fullmatch(normalized):
            raise ValueError("Initials must be exactly 3 capital letters or numbers.")
        return normalized

    @field_validator("screen_name")
    @classmethod
    def validate_screen_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Screen name cannot be empty.")
        return cleaned

class Player(PlayerBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class PlayerPublic(BaseModel):
    id: int
    initials: str
    screen_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LastGameSummary(BaseModel):
    id: int
    machine_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    score: Optional[int] = None


class PlayerStats(BaseModel):
    total_games: int
    best_score: Optional[int] = None
    last_game: Optional[LastGameSummary] = None


class PlayerDetail(PlayerPublic):
    stats: PlayerStats

class GameStateBase(BaseModel):
    seconds_elapsed: int
    ball: int
    player_up: int
    scores: Dict[str, int] # Assuming scores is a dict of player_id/index to score

class GameStateCreate(GameStateBase):
    game_id: int

class GameState(GameStateBase):
    id: int
    game_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class GameBase(BaseModel):
    machine_id: int
    is_active: bool = True

class GameCreate(GameBase):
    pass

class Game(GameBase):
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BallPlayTime(BaseModel):
    ball: int
    seconds: int
    score: int = 0
    is_current: bool = False


class LiveScore(BaseModel):
    player_id: Optional[int] = None
    player_number: int
    initials: Optional[str] = None
    screen_name: Optional[str] = None
    score: int
    total_play_seconds: int = 0
    ball_times: List[BallPlayTime] = Field(default_factory=list)
    is_player_up: bool = False


class LiveGameState(BaseModel):
    game_id: int
    machine_id: int
    machine_uid: Optional[str] = None
    machine_name: Optional[str] = None
    machine_ip: Optional[str] = None
    is_active: bool
    seconds_elapsed: int
    ball: int
    player_up: int
    updated_at: datetime
    scores: List[LiveScore]

    model_config = ConfigDict(from_attributes=True)


class GameWithMachine(Game):
    machine_name: Optional[str] = None
    machine_ip: Optional[str] = None
    machine_last_seen: Optional[datetime] = None
    machine_uid: Optional[str] = None
    machine_version: Optional[str] = None
    machine_version_checked_at: Optional[datetime] = None
    has_password: bool = False


class GamePasswordUpdate(BaseModel):
    password: str = Field(min_length=4)


class GamePasswordStatus(BaseModel):
    id: int
    has_password: bool


class MachineVersionStatus(BaseModel):
    machine_version: Optional[str] = None
    machine_version_checked_at: Optional[datetime] = None


class UpdateApplyRequest(BaseModel):
    url: str


class LeaderboardEntry(BaseModel):
    player_id: int
    player_number: int
    initials: str
    screen_name: Optional[str] = None
    score: int
    last_played: Optional[datetime] = None
    machine_name: Optional[str] = None


class LeaderboardGame(BaseModel):
    id: int
    machine_name: str
    is_active: bool
    start_time: datetime
    end_time: Optional[datetime] = None
    leaderboard: List[LeaderboardEntry]


class TimeWindowLeaderboard(BaseModel):
    slug: str
    title: str
    since: Optional[datetime] = None
    leaderboard: List[LeaderboardEntry]


class GameLeaderboardBundle(BaseModel):
    id: int
    machine_name: str
    is_active: bool
    windows: List[TimeWindowLeaderboard]
    champion: Optional[LeaderboardEntry] = None
    last_activity_at: Optional[datetime] = None


class LeaderboardSummary(BaseModel):
    games: List[GameLeaderboardBundle]
    leaderboards: List[TimeWindowLeaderboard]
    total_boards: int
    tournaments: List[TournamentBoard] = Field(default_factory=list)


class GameModeBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    activation_payload: Optional[dict] = None


class GameModeCreate(GameModeBase):
    pass


class GameMode(GameModeBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaderboardProfileBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    sql_template: str
    sort_direction: Literal["asc", "desc"] = "desc"


class LeaderboardProfileCreate(LeaderboardProfileBase):
    pass


class LeaderboardProfile(LeaderboardProfileBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TournamentType(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    scoring_profile_slug: str
    game_mode_slug: Optional[str] = None


class TournamentBase(BaseModel):
    name: str
    tournament_type: str
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    display_until: Optional[datetime] = None
    is_active: bool = True

    @field_validator("display_until")
    @classmethod
    def validate_display_window(
        cls, value: Optional[datetime], info: ValidationInfo
    ) -> Optional[datetime]:
        end_time = (info.data or {}).get("end_time") if info else None
        if value is not None and end_time is not None and value < end_time:
            raise ValueError("display_until must be after the tournament end_time.")
        return value


class TournamentCreate(TournamentBase):
    machine_ids: List[int] = Field(default_factory=list)
    player_ids: List[int] = Field(default_factory=list)


class TournamentMachineLink(BaseModel):
    machine_id: int

    model_config = ConfigDict(from_attributes=True)


class TournamentPlayerLink(BaseModel):
    player_id: int

    model_config = ConfigDict(from_attributes=True)


class Tournament(TournamentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    scoring_profile: LeaderboardProfile
    game_mode: Optional[GameMode] = None
    tournament_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TournamentDetail(Tournament):
    scoring_profile: Optional[LeaderboardProfile] = None
    game_mode: Optional[GameMode] = None
    machines: List[TournamentMachineLink] = Field(default_factory=list)
    players: List[TournamentPlayerLink] = Field(default_factory=list)


class TournamentStanding(BaseModel):
    player_id: int
    initials: str
    screen_name: Optional[str] = None
    score: int
    last_played: Optional[datetime] = None


class TournamentBoard(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    display_until: Optional[datetime] = None
    is_active: bool = True
    scoring_profile: Optional[LeaderboardProfile] = None
    game_mode: Optional[GameMode] = None
    leaderboard: List[TournamentStanding] = Field(default_factory=list)
    last_activity_at: Optional[datetime] = None
