from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .. import crud
from ..auth import get_current_user

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
def create_tournament(
    tournament: TournamentBase,
    current_user: crud.models.User = Depends(get_current_user),
) -> Tournament:
    new_id = len(_tournaments) + 1
    t = Tournament(id=new_id, owner_id=current_user.id, **tournament.model_dump())
    _tournaments.append(t)
    return t

FILTER_WINDOWS = {"today": 1, "next7": 7, "next30": 30}


@router.get("/", response_model=List[Tournament])
def list_tournaments(
    filter: str | None = Query(default=None),
    current_user: crud.models.User = Depends(get_current_user),
) -> List[Tournament]:
    now = datetime.utcnow()
    today = datetime(now.year, now.month, now.day)

    if filter in FILTER_WINDOWS:
        start = today
        end = start + timedelta(days=FILTER_WINDOWS[filter])
        return [t for t in _tournaments if start <= t.start_time < end]

    return _tournaments


@router.get("/{tournament_id}", response_model=Tournament)
def get_tournament(
    tournament_id: int, current_user: crud.models.User = Depends(get_current_user)
) -> Tournament:
    return _get_tournament(tournament_id)


@router.post("/{tournament_id}/register", response_model=Tournament)
def register_user(
    tournament_id: int, current_user: crud.models.User = Depends(get_current_user)
) -> Tournament:
    t = _get_tournament(tournament_id)
    if current_user.id not in t.registered_users:
        t.registered_users.append(current_user.id)
    return t


@router.post("/{tournament_id}/join", response_model=Tournament)
def join_tournament(
    tournament_id: int, current_user: crud.models.User = Depends(get_current_user)
) -> Tournament:
    t = _get_tournament(tournament_id)
    if current_user.id not in t.joined_users:
        t.joined_users.append(current_user.id)
    return t


class TournamentUpdate(BaseModel):
    allow_invites: bool


@router.patch("/{tournament_id}", response_model=Tournament)
def update_tournament(
    tournament_id: int,
    update: TournamentUpdate,
    current_user: crud.models.User = Depends(get_current_user),
) -> Tournament:
    t = _get_tournament(tournament_id)
    if t.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update")
    t.allow_invites = update.allow_invites
    return t
