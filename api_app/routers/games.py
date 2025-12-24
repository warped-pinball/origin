from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from .. import database, models, schemas

LIVE_STALE_SECONDS = 60


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

router = APIRouter(prefix="/games", tags=["games"])


async def _latest_state(db: AsyncSession, game_id: int) -> Optional[models.GameState]:
    result = await db.execute(
        select(models.GameState)
        .where(models.GameState.game_id == game_id)
        .order_by(models.GameState.timestamp.desc())
        .limit(1)
    )
    return result.scalars().first()


async def _all_states(db: AsyncSession, game_id: int) -> list[models.GameState]:
    result = await db.execute(
        select(models.GameState)
        .where(models.GameState.game_id == game_id)
        .order_by(models.GameState.timestamp.asc())
    )
    return result.scalars().all()


def _parse_scores(raw_scores) -> dict[int, int]:
    parsed: dict[int, int] = {}
    if isinstance(raw_scores, dict):
        iterable = raw_scores.items()
    elif isinstance(raw_scores, list):
        iterable = ((idx + 1, value) for idx, value in enumerate(raw_scores))
    else:
        iterable = []

    for key, value in iterable:
        try:
            player_number = int(key)
            parsed[player_number] = int(value or 0)
        except (TypeError, ValueError):
            continue
    return parsed


def _collect_play_stats(
    states: list[models.GameState],
) -> tuple[dict[int, dict[str, object]], Optional[int]]:
    timelines: dict[int, dict[int, dict[str, int | None]]] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "start_time": None,
                "end_time": None,
                "start_score": None,
                "end_score": None,
            }
        )
    )
    previous_scores: dict[int, int] = {}
    last_scorer: Optional[int] = None
    last_state_second = 0

    for state in states:
        scores = _parse_scores(state.scores or {})
        priors: dict[int, int] = {}
        active_players: set[int] = set()

        for player_number, score in scores.items():
            prior_score = previous_scores.get(player_number, score)
            priors[player_number] = prior_score
            if prior_score != score:
                active_players.add(player_number)
                last_scorer = player_number

        if not active_players and scores:
            active_players.add(state.player_up or min(scores))

        for player_number in active_players:
            score = scores.get(player_number, previous_scores.get(player_number, 0))
            prior_score = priors.get(player_number, score)
            bucket = timelines[player_number][state.ball]
            if bucket["start_time"] is None:
                bucket["start_time"] = state.seconds_elapsed
                bucket["start_score"] = prior_score

            bucket["end_time"] = state.seconds_elapsed
            bucket["end_score"] = score

        for player_number, score in scores.items():
            previous_scores[player_number] = score

        last_state_second = state.seconds_elapsed

    active_ball = states[-1].ball if states else None

    totals: dict[int, dict[str, object]] = {}
    for player_number, balls in timelines.items():
        total_seconds = 0
        ball_times: list[schemas.BallPlayTime] = []
        for ball, bounds in sorted(balls.items()):
            start = bounds["start_time"]
            end = bounds["end_time"] if bounds["end_time"] is not None else last_state_second
            start_score = bounds.get("start_score") or 0
            end_score = bounds.get("end_score") or start_score

            if start is None:
                continue

            elapsed = max(end - start, 0)
            score_delta = max(end_score - start_score, 0)
            total_seconds += elapsed
            ball_times.append(
                schemas.BallPlayTime(
                    ball=ball,
                    seconds=int(elapsed),
                    score=int(score_delta),
                    is_current=ball == active_ball,
                )
            )

        totals[player_number] = {
            "total_seconds": total_seconds,
            "ball_times": ball_times,
        }

    return totals, last_scorer


async def _build_live_state(
    db: AsyncSession, game: models.Game
) -> Optional[schemas.LiveGameState]:
    states = await _all_states(db, game.id)
    if not states:
        return None

    state = states[-1]
    latest_timestamp = _ensure_utc(state.timestamp)
    if latest_timestamp:
        age = (datetime.now(timezone.utc) - latest_timestamp).total_seconds()
        if age > LIVE_STALE_SECONDS:
            return None

    player_scores: list[schemas.LiveScore] = []
    scores = _parse_scores(state.scores or {})
    if not scores:
        return None

    play_times, last_scorer = _collect_play_stats(states)

    active_player = last_scorer or state.player_up or 1

    for game_player in sorted(game.game_players, key=lambda gp: gp.player_number):
        player = game_player.player
        score_value = scores.get(game_player.player_number, 0)
        durations = play_times.get(game_player.player_number, {})
        ball_times = [
            schemas.BallPlayTime(
                ball=bt.ball,
                seconds=bt.seconds,
                score=bt.score,
                is_current=bt.ball == state.ball and game_player.player_number == active_player,
            )
            for bt in durations.get("ball_times", [])
        ]
        player_scores.append(
            schemas.LiveScore(
                player_id=player.id if player else None,
                player_number=game_player.player_number,
                initials=player.initials if player else None,
                screen_name=player.screen_name if player else None,
                score=score_value,
                total_play_seconds=int(durations.get("total_seconds", 0)),
                ball_times=ball_times,
                is_player_up=game_player.player_number == active_player,
            )
        )

    for player_number, score_value in sorted(scores.items()):
        if any(entry.player_number == player_number for entry in player_scores):
            continue
        durations = play_times.get(player_number, {})
        ball_times = [
            schemas.BallPlayTime(
                ball=bt.ball,
                seconds=bt.seconds,
                score=bt.score,
                is_current=bt.ball == state.ball and player_number == active_player,
            )
            for bt in durations.get("ball_times", [])
        ]
        player_scores.append(
            schemas.LiveScore(
                player_id=None,
                player_number=player_number,
                initials=None,
                screen_name=None,
                score=score_value,
                total_play_seconds=int(durations.get("total_seconds", 0)),
                ball_times=ball_times,
                is_player_up=player_number == active_player,
            )
        )

    return schemas.LiveGameState(
        game_id=game.id,
        machine_id=game.machine_id,
        machine_uid=game.machine.uid if game.machine else None,
        machine_name=game.machine.name if game.machine else None,
        machine_ip=game.machine.ip_address if game.machine else None,
        is_active=game.is_active,
        seconds_elapsed=state.seconds_elapsed,
        ball=state.ball,
        player_up=active_player,
        updated_at=state.timestamp,
        scores=player_scores,
    )


@router.post("/", response_model=schemas.Game)
async def create_game(game: schemas.GameCreate, db: AsyncSession = Depends(database.get_db)):
    db_game = models.Game(**game.model_dump())
    db.add(db_game)
    await db.commit()
    await db.refresh(db_game)
    return db_game


@router.get("/", response_model=List[schemas.Game])
async def read_games(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Game).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/discovered", response_model=List[schemas.GameWithMachine])
async def discovered_games(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(
        select(models.Game)
        .join(models.Game.machine)
        .options(selectinload(models.Game.machine))
        .where(models.Game.is_active.is_(True))
        .order_by(models.Machine.last_seen.desc(), models.Game.id.desc())
    )

    seen_uids = set()
    games = []

    for game in result.scalars().unique().all():
        uid = game.machine.uid if game.machine else None
        if uid and uid in seen_uids:
            continue
        if uid:
            seen_uids.add(uid)
        games.append(game)

    return [
        schemas.GameWithMachine(
            id=game.id,
            machine_id=game.machine_id,
            start_time=game.start_time,
            end_time=game.end_time,
            is_active=game.is_active,
            machine_name=game.machine.name if game.machine else None,
            machine_ip=game.machine.ip_address if game.machine else None,
            machine_last_seen=game.machine.last_seen if game.machine else None,
            machine_uid=game.machine.uid if game.machine else None,
            machine_version=game.machine.version if game.machine else None,
            machine_version_checked_at=game.machine.version_checked_at if game.machine else None,
            has_password=bool(game.admin_password),
        )
        for game in games
    ]


@router.get("/live", response_model=List[schemas.LiveGameState])
async def live_games(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(
        select(models.Game)
            .where(models.Game.is_active.is_(True))
            .options(
                selectinload(models.Game.machine),
                selectinload(models.Game.game_players).selectinload(models.GamePlayer.player),
            )
            .order_by(models.Game.id)
    )

    games = result.scalars().unique().all()
    live_states: list[schemas.LiveGameState] = []

    for game in games:
        live_state = await _build_live_state(db, game)
        if live_state:
            live_states.append(live_state)

    return live_states


@router.get("/{game_id}/live", response_model=schemas.LiveGameState)
async def live_game(
    game_id: int, db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(
        select(models.Game)
        .where(models.Game.id == game_id)
        .options(
            selectinload(models.Game.machine),
            selectinload(models.Game.game_players).selectinload(models.GamePlayer.player),
        )
    )
    game = result.scalars().first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    live_state = await _build_live_state(db, game)
    if not live_state:
        raise HTTPException(status_code=404, detail="No game state available")

    return live_state


@router.get("/{game_id}", response_model=schemas.Game)
async def read_game(game_id: int, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Game).where(models.Game.id == game_id))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game
