from typing import List
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/tournaments", tags=["tournaments"])

class TournamentBase(BaseModel):
    name: str
    start_time: datetime
    rule_set: str
    public: bool

class Tournament(TournamentBase):
    id: int

# In-memory store for demo purposes
_tournaments: List[Tournament] = []

@router.post("/", response_model=Tournament)
def create_tournament(tournament: TournamentBase) -> Tournament:
    new_id = len(_tournaments) + 1
    t = Tournament(id=new_id, **tournament.dict())
    _tournaments.append(t)
    return t

@router.get("/", response_model=List[Tournament])
def list_tournaments() -> List[Tournament]:
    return _tournaments
