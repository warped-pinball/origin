import re
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import database, models, schemas
from .admin import _verify_admin

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


TOURNAMENT_TYPES: dict[str, dict[str, object]] = {
    "high-score": {
        "name": "High Score Showdown",
        "description": "Classic tournament where the highest score wins across selected machines.",
        "scoring_profile_slug": "high-score",
        "game_mode_slug": "standard",
    },
    "limbo": {
        "name": "Limbo Weekend",
        "description": "Lowest score wins—perfect for quirky house rules or pin-golf setups.",
        "scoring_profile_slug": "limbo",
        "game_mode_slug": "pin-golf",
    },
}


def _derive_times(payload: schemas.TournamentBase) -> tuple[datetime, datetime, datetime]:
    start_time = payload.start_time or datetime.utcnow()
    end_time = payload.end_time or start_time + timedelta(hours=2)
    display_until = payload.display_until or end_time + timedelta(hours=1)
    return start_time, end_time, display_until


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned or "tournament"


async def _generate_unique_slug(db: AsyncSession, base_slug: str, existing_id: int | None = None) -> str:
    candidate = base_slug
    counter = 2
    while True:
        query = select(models.Tournament.id).where(models.Tournament.slug == candidate)
        if existing_id is not None:
            query = query.where(models.Tournament.id != existing_id)

        result = await db.execute(query)
        if result.scalar_one_or_none() is None:
            return candidate

        candidate = f"{base_slug}-{counter}"
        counter += 1


def _apply_tournament_type(tournament: models.Tournament) -> models.Tournament:
    for slug, config in TOURNAMENT_TYPES.items():
        if tournament.scoring_profile and tournament.scoring_profile.slug != config["scoring_profile_slug"]:
            continue

        expected_mode = config.get("game_mode_slug")
        tournament_mode_slug = tournament.game_mode.slug if tournament.game_mode else None
        if expected_mode != tournament_mode_slug:
            continue

        tournament.tournament_type = slug
        break
    return tournament


async def _get_tournament(db: AsyncSession, tournament_id: int) -> models.Tournament:
    result = await db.execute(
        select(models.Tournament)
        .where(models.Tournament.id == tournament_id)
        .options(
            selectinload(models.Tournament.scoring_profile),
            selectinload(models.Tournament.game_mode),
            selectinload(models.Tournament.machines).selectinload(models.TournamentMachine.machine),
            selectinload(models.Tournament.players).selectinload(models.TournamentPlayer.player),
        )
    )
    tournament = result.scalar_one_or_none()
    if tournament is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    return _apply_tournament_type(tournament)


@router.get("/profiles", response_model=List[schemas.LeaderboardProfile])
async def list_leaderboard_profiles(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.LeaderboardProfile).order_by(models.LeaderboardProfile.created_at))
    return result.scalars().all()


@router.get("/types", response_model=List[schemas.TournamentType])
async def list_tournament_types():
    return [
        schemas.TournamentType(slug=slug, **config) for slug, config in sorted(TOURNAMENT_TYPES.items())
    ]


@router.post(
    "/profiles",
    response_model=schemas.LeaderboardProfile,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_verify_admin)],
)
async def create_leaderboard_profile(
    payload: schemas.LeaderboardProfileCreate, db: AsyncSession = Depends(database.get_db)
):
    existing = await db.execute(
        select(models.LeaderboardProfile).where(models.LeaderboardProfile.slug == payload.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")

    profile = models.LeaderboardProfile(**payload.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/modes", response_model=List[schemas.GameMode])
async def list_game_modes(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.GameMode).order_by(models.GameMode.created_at))
    return result.scalars().all()


@router.post(
    "/modes",
    response_model=schemas.GameMode,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_verify_admin)],
)
async def create_game_mode(payload: schemas.GameModeCreate, db: AsyncSession = Depends(database.get_db)):
    existing = await db.execute(select(models.GameMode).where(models.GameMode.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")

    mode = models.GameMode(**payload.model_dump())
    db.add(mode)
    await db.commit()
    await db.refresh(mode)
    return mode


@router.get("", response_model=List[schemas.TournamentDetail])
@router.get("/", response_model=List[schemas.TournamentDetail])
async def list_tournaments(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(
        select(models.Tournament)
        .options(
            selectinload(models.Tournament.scoring_profile),
            selectinload(models.Tournament.game_mode),
            selectinload(models.Tournament.machines).selectinload(models.TournamentMachine.machine),
            selectinload(models.Tournament.players).selectinload(models.TournamentPlayer.player),
        )
        .order_by(models.Tournament.start_time)
    )
    return [_apply_tournament_type(record) for record in result.scalars().all()]


@router.get("/{tournament_id}", response_model=schemas.TournamentDetail)
async def get_tournament(tournament_id: int, db: AsyncSession = Depends(database.get_db)):
    tournament = await _get_tournament(db, tournament_id)
    return tournament


@router.post(
    "",
    response_model=schemas.TournamentDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_verify_admin)],
)
@router.post(
    "/",
    response_model=schemas.TournamentDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_verify_admin)],
)
async def create_tournament(payload: schemas.TournamentCreate, db: AsyncSession = Depends(database.get_db)):
    tournament_type = TOURNAMENT_TYPES.get(payload.tournament_type)
    if not tournament_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown tournament type '{payload.tournament_type}'",
        )

    profile = await db.execute(
        select(models.LeaderboardProfile).where(
            models.LeaderboardProfile.slug == tournament_type["scoring_profile_slug"]
        )
    )
    scoring_profile = profile.scalar_one_or_none()
    if scoring_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scoring profile not found")

    game_mode = None
    game_mode_slug = tournament_type.get("game_mode_slug")
    if game_mode_slug:
        result = await db.execute(select(models.GameMode).where(models.GameMode.slug == game_mode_slug))
        game_mode = result.scalar_one_or_none()
        if game_mode is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game mode not found")

    start_time, end_time, display_until = _derive_times(payload)

    base_slug = f"{payload.tournament_type}-{_slugify(payload.name)}"
    slug = await _generate_unique_slug(db, base_slug)

    tournament = models.Tournament(
        name=payload.name,
        slug=slug,
        description=payload.description,
        scoring_profile=scoring_profile,
        game_mode=game_mode,
        start_time=start_time,
        end_time=end_time,
        display_until=display_until,
        is_active=True,
    )
    tournament.tournament_type = payload.tournament_type

    if payload.machine_ids:
        machines = await db.execute(select(models.Machine).where(models.Machine.id.in_(payload.machine_ids)))
        machine_records = machines.scalars().all()
        found_ids = {machine.id for machine in machine_records}
        missing = set(payload.machine_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machines not found: {', '.join(map(str, sorted(missing)))}",
            )
        tournament.machines = [models.TournamentMachine(machine=machine) for machine in machine_records]

    if payload.player_ids:
        players = await db.execute(select(models.Player).where(models.Player.id.in_(payload.player_ids)))
        player_records = players.scalars().all()
        found_ids = {player.id for player in player_records}
        missing = set(payload.player_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Players not found: {', '.join(map(str, sorted(missing)))}",
            )
        tournament.players = [models.TournamentPlayer(player=player) for player in player_records]

    db.add(tournament)
    await db.commit()
    await db.refresh(tournament)
    return await _get_tournament(db, tournament.id)


@router.patch(
    "/{tournament_id}",
    response_model=schemas.TournamentDetail,
    dependencies=[Depends(_verify_admin)],
)
async def update_tournament(
    tournament_id: int, payload: schemas.TournamentCreate, db: AsyncSession = Depends(database.get_db)
):
    tournament = await _get_tournament(db, tournament_id)

    tournament_type = TOURNAMENT_TYPES.get(payload.tournament_type)
    if not tournament_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown tournament type '{payload.tournament_type}'",
        )

    profile = await db.execute(
        select(models.LeaderboardProfile).where(
            models.LeaderboardProfile.slug == tournament_type["scoring_profile_slug"]
        )
    )
    scoring_profile = profile.scalar_one_or_none()
    if scoring_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scoring profile not found")

    game_mode = None
    game_mode_slug = tournament_type.get("game_mode_slug")
    if game_mode_slug:
        result = await db.execute(select(models.GameMode).where(models.GameMode.slug == game_mode_slug))
        game_mode = result.scalar_one_or_none()
        if game_mode is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game mode not found")

    start_time, end_time, display_until = _derive_times(payload)

    tournament.name = payload.name
    base_slug = f"{payload.tournament_type}-{_slugify(payload.name)}"
    tournament.slug = await _generate_unique_slug(db, base_slug, existing_id=tournament.id)
    tournament.description = payload.description
    tournament.scoring_profile = scoring_profile
    tournament.game_mode = game_mode
    tournament.start_time = start_time
    tournament.end_time = end_time
    tournament.display_until = display_until
    tournament.is_active = True
    tournament.tournament_type = payload.tournament_type

    tournament.machines.clear()
    if payload.machine_ids:
        machines = await db.execute(select(models.Machine).where(models.Machine.id.in_(payload.machine_ids)))
        machine_records = machines.scalars().all()
        found_ids = {machine.id for machine in machine_records}
        missing = set(payload.machine_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machines not found: {', '.join(map(str, sorted(missing)))}",
            )
        tournament.machines = [models.TournamentMachine(machine=machine) for machine in machine_records]

    tournament.players.clear()
    if payload.player_ids:
        players = await db.execute(select(models.Player).where(models.Player.id.in_(payload.player_ids)))
        player_records = players.scalars().all()
        found_ids = {player.id for player in player_records}
        missing = set(payload.player_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Players not found: {', '.join(map(str, sorted(missing)))}",
            )
        tournament.players = [models.TournamentPlayer(player=player) for player in player_records]

    await db.commit()
    await db.refresh(tournament)
    return await _get_tournament(db, tournament.id)


@router.delete(
    "/{tournament_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_verify_admin)],
)
async def delete_tournament(tournament_id: int, db: AsyncSession = Depends(database.get_db)):
    tournament = await _get_tournament(db, tournament_id)
    await db.delete(tournament)
    await db.commit()
