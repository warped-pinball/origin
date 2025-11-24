from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class MachineBase(BaseModel):
    name: str
    ip_address: str


class MachineCreate(MachineBase):
    pass


class Machine(MachineBase):
    id: int
    last_seen: datetime

    class Config:
        orm_mode = True


class GameStateBase(BaseModel):
    seconds_elapsed: int
    ball: int
    player_up: int
    scores: List[int]


class GameStateCreate(GameStateBase):
    machine_id: int
    # timestamp is optional as it can be set by server if missing
    timestamp: Optional[datetime] = None


class GameState(GameStateBase):
    id: int
    game_id: int
    timestamp: datetime

    class Config:
        orm_mode = True


class GameBase(BaseModel):
    machine_id: int
    is_active: bool = True


class Game(GameBase):
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None

    class Config:
        orm_mode = True
