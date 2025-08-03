from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/tournaments", tags=["tournaments"])

class TournamentBase(BaseModel):
    name: str
    start_time: datetime
    rule_set: str
    public: bool
    allow_invites: bool = False

class Tournament(TournamentBase):
    id: int
    owner_id: int
    registered_users: List[int] = Field(default_factory=list)
    joined_users: List[int] = Field(default_factory=list)

# In-memory store for demo purposes
_tournaments: List[Tournament] = []

def _get_tournament(tournament_id: int) -> Tournament:
    for t in _tournaments:
        if t.id == tournament_id:
            return t
    raise HTTPException(status_code=404, detail="Tournament not found")


@router.post("/", response_model=Tournament)
def create_tournament(tournament: TournamentBase) -> Tournament:
    new_id = len(_tournaments) + 1
    t = Tournament(id=new_id, owner_id=1, **tournament.dict())
    _tournaments.append(t)
    return t

@router.get("/", response_model=List[Tournament])
def list_tournaments(filter: str | None = Query(default=None)) -> List[Tournament]:
    now = datetime.utcnow()
    if filter == "today":
        start = datetime(now.year, now.month, now.day)
        end = start + timedelta(days=1)
    elif filter == "next7":
        start = now
        end = now + timedelta(days=7)
    elif filter == "next30":
        start = now
        end = now + timedelta(days=30)
    else:
        return _tournaments
    return [t for t in _tournaments if start <= t.start_time < end]


class UserAction(BaseModel):
    user_id: int


@router.get("/{tournament_id}", response_model=Tournament)
def get_tournament(tournament_id: int) -> Tournament:
    return _get_tournament(tournament_id)


@router.post("/{tournament_id}/register", response_model=Tournament)
def register_user(tournament_id: int, action: UserAction) -> Tournament:
    t = _get_tournament(tournament_id)
    if action.user_id not in t.registered_users:
        t.registered_users.append(action.user_id)
    return t


@router.post("/{tournament_id}/join", response_model=Tournament)
def join_tournament(tournament_id: int, action: UserAction) -> Tournament:
    t = _get_tournament(tournament_id)
    if action.user_id not in t.joined_users:
        t.joined_users.append(action.user_id)
    return t


class TournamentUpdate(BaseModel):
    allow_invites: bool


@router.patch("/{tournament_id}", response_model=Tournament)
def update_tournament(tournament_id: int, update: TournamentUpdate) -> Tournament:
    t = _get_tournament(tournament_id)
    t.allow_invites = update.allow_invites
    return t
