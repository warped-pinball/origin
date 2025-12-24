from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import database, models, schemas

router = APIRouter(prefix="/players", tags=["players"])

ALLOWED_INITIAL_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


async def _fetch_taken_initials(db: AsyncSession) -> set[str]:
    result = await db.execute(select(models.Player.initials))
    return {value.upper() for value in result.scalars().all()}


def _generate_initial_suggestions(initials: str, taken: set[str], limit: int = 3) -> list[str]:
    suggestions: list[str] = []

    def _collect(prefix: str) -> None:
        nonlocal suggestions
        for char in ALLOWED_INITIAL_CHARS:
            if len(suggestions) >= limit:
                return
            candidate = f"{prefix}{char}"
            if candidate == initials or candidate in taken:
                continue
            suggestions.append(candidate)

    _collect(initials[:2])

    if len(suggestions) < limit:
        for second in ALLOWED_INITIAL_CHARS:
            if len(suggestions) >= limit:
                break
            _collect(f"{initials[0]}{second}")

    if len(suggestions) < limit:
        for first in ALLOWED_INITIAL_CHARS:
            if len(suggestions) >= limit:
                break
            for second in ALLOWED_INITIAL_CHARS:
                if len(suggestions) >= limit:
                    break
                _collect(f"{first}{second}")

    return suggestions[:limit]


async def _ensure_unique_initials(db: AsyncSession, initials: str, exclude_player_id: int | None = None) -> None:
    query = select(models.Player.id).where(func.upper(models.Player.initials) == initials.upper())
    if exclude_player_id is not None:
        query = query.where(models.Player.id != exclude_player_id)

    result = await db.execute(query)
    if result.scalar_one_or_none() is not None:
        taken = await _fetch_taken_initials(db)
        suggestions = _generate_initial_suggestions(initials.upper(), taken)
        detail = {
            "message": f"Initials {initials.upper()} are already taken.",
            "suggestions": suggestions,
        }
        raise HTTPException(status_code=400, detail=detail)


def _build_search_filter(search: str):
    term = f"%{search.lower()}%"
    return or_(
        func.lower(models.Player.initials).like(term),
        func.lower(models.Player.screen_name).like(term),
        func.lower(models.Player.first_name).like(term),
        func.lower(models.Player.last_name).like(term),
        func.lower(models.Player.email).like(term),
        func.lower(models.Player.phone_number).like(term),
        func.lower(
            func.trim(
                func.concat(
                    func.coalesce(models.Player.first_name, ""),
                    " ",
                    func.coalesce(models.Player.last_name, ""),
                )
            )
        ).like(term),
    )


@router.post("/", response_model=schemas.PlayerPublic)
async def create_player(player: schemas.PlayerCreate, db: AsyncSession = Depends(database.get_db)):
    await _ensure_unique_initials(db, player.initials)
    db_player = models.Player(**player.model_dump())
    db.add(db_player)
    await db.commit()
    await db.refresh(db_player)
    return db_player


@router.get("/", response_model=List[schemas.PlayerPublic])
async def read_players(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    db: AsyncSession = Depends(database.get_db),
):
    query = select(models.Player).offset(skip).limit(limit)
    if search:
        query = query.where(_build_search_filter(search))

    result = await db.execute(query)
    return result.scalars().all()


def _latest_scores(game: models.Game) -> dict:
    if not game.game_states:
        return {}

    latest_state = max(game.game_states, key=lambda state: state.timestamp or datetime.min)
    return latest_state.scores or {}


def _score_for_player(scores: dict, player_number: int) -> int:
    return int(scores.get(str(player_number)) or scores.get(player_number, 0) or 0)


async def _build_player_stats(db: AsyncSession, player_id: int) -> schemas.PlayerStats:
    result = await db.execute(
        select(models.GamePlayer)
        .join(models.Game)
        .options(
            selectinload(models.GamePlayer.game).selectinload(models.Game.game_states),
            selectinload(models.GamePlayer.game).selectinload(models.Game.machine),
        )
        .where(models.GamePlayer.player_id == player_id)
    )

    game_players = result.scalars().all()
    total_games = len(game_players)
    best_score: Optional[int] = None
    last_game: Optional[schemas.LastGameSummary] = None

    for game_player in game_players:
        game = game_player.game
        if not game:
            continue

        scores = _latest_scores(game)
        score = _score_for_player(scores, game_player.player_number)
        best_score = max(best_score or 0, score) if best_score is not None else score

        if last_game is None or (game.start_time and game.start_time > (last_game.start_time or game.start_time)):
            last_game = schemas.LastGameSummary(
                id=game.id,
                machine_name=game.machine.name if game.machine else None,
                start_time=game.start_time,
                end_time=game.end_time,
                score=score,
            )

    return schemas.PlayerStats(total_games=total_games, best_score=best_score, last_game=last_game)


async def _build_player_detail(db: AsyncSession, player: models.Player) -> schemas.PlayerDetail:
    stats = await _build_player_stats(db, player.id)
    return schemas.PlayerDetail(
        id=player.id,
        initials=player.initials,
        screen_name=player.screen_name,
        first_name=player.first_name,
        last_name=player.last_name,
        stats=stats,
    )


@router.get("/{player_id}", response_model=schemas.PlayerDetail)
async def read_player(player_id: int, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Player).where(models.Player.id == player_id))
    player = result.scalar_one_or_none()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return await _build_player_detail(db, player)


@router.put("/{player_id}", response_model=schemas.PlayerDetail)
async def update_player(player_id: int, player_update: schemas.PlayerUpdate, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Player).where(models.Player.id == player_id))
    db_player = result.scalar_one_or_none()
    if db_player is None:
        raise HTTPException(status_code=404, detail="Player not found")

    update_data = player_update.model_dump(exclude_unset=True)
    if "initials" in update_data:
        await _ensure_unique_initials(db, update_data["initials"], exclude_player_id=player_id)

    if not (update_data.get("phone_number") or update_data.get("email")):
        raise HTTPException(
            status_code=400,
            detail="Provide a phone number or email address to save changes.",
        )

    for key, value in update_data.items():
        setattr(db_player, key, value)

    await db.commit()
    await db.refresh(db_player)
    return await _build_player_detail(db, db_player)
