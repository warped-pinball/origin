from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import bindparam, select, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from .. import database, models, schemas

router = APIRouter(tags=["leaderboard"])


def _latest_scores(game: models.Game) -> dict:
    if not game.game_states:
        return {}

    latest_state = _latest_state(game)
    return latest_state.scores or {}


def _score_for_player(scores: dict, player_number: int) -> int:
    return int(scores.get(str(player_number)) or scores.get(player_number, 0) or 0)


def _coerce_timestamp(timestamp: datetime | None) -> datetime | None:
    if not timestamp:
        return None
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp)
        except ValueError:
            return None
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp


def _latest_state(game: models.Game) -> models.GameState | None:
    if not game.game_states:
        return None

    return max(
        game.game_states,
        key=lambda state: state.timestamp or datetime.min,
    )


def _latest_state_timestamp(game: models.Game) -> datetime | None:
    state = _latest_state(game)
    if state:
        return _coerce_timestamp(state.timestamp)
    return _coerce_timestamp(game.end_time or game.start_time)


def _game_last_activity(game: models.Game) -> datetime | None:
    timestamp = _latest_state_timestamp(game)
    if timestamp:
        return timestamp
    if game.updated_at:
        return _coerce_timestamp(game.updated_at)
    return _coerce_timestamp(game.start_time)


def _build_leaderboard(game: models.Game) -> schemas.LeaderboardGame:
    scores = _latest_scores(game)
    entries: list[schemas.LeaderboardEntry] = []

    for game_player in game.game_players:
        player = game_player.player
        entries.append(
            schemas.LeaderboardEntry(
                player_id=player.id,
                player_number=game_player.player_number,
                initials=player.initials,
                screen_name=player.screen_name,
                score=_score_for_player(scores, game_player.player_number),
                last_played=_latest_state_timestamp(game),
                machine_name=game.machine.name if game.machine else None,
            )
        )

    entries.sort(key=lambda entry: entry.score, reverse=True)

    return schemas.LeaderboardGame(
        id=game.id,
        machine_name=game.machine.name if game.machine else "Unknown",
        is_active=game.is_active,
        start_time=game.start_time,
        end_time=game.end_time,
        leaderboard=entries,
    )


def _player_snapshots(games: Iterable[models.Game]) -> list[schemas.LeaderboardEntry]:
    snapshots: list[schemas.LeaderboardEntry] = []

    for game in games:
        scores = _latest_scores(game)
        observed_at = _latest_state_timestamp(game)
        for game_player in game.game_players:
            player = game_player.player
            snapshots.append(
                schemas.LeaderboardEntry(
                    player_id=player.id,
                    player_number=game_player.player_number,
                    initials=player.initials,
                    screen_name=player.screen_name,
                    score=_score_for_player(scores, game_player.player_number),
                    last_played=observed_at,
                    machine_name=game.machine.name if game.machine else None,
                )
            )

    return snapshots


def _aggregate_by_timeframe(
    snapshots: Iterable[schemas.LeaderboardEntry], since: datetime | None
) -> list[schemas.LeaderboardEntry]:
    best_scores: dict[int, schemas.LeaderboardEntry] = {}

    for snapshot in snapshots:
        last_played = _coerce_timestamp(snapshot.last_played)
        if since and last_played and last_played < since:
            continue

        existing = best_scores.get(snapshot.player_id)
        if not existing:
            best_scores[snapshot.player_id] = snapshot
            continue

        if snapshot.score > existing.score or (
            snapshot.score == existing.score
            and (_coerce_timestamp(snapshot.last_played) or datetime.min)
            > (_coerce_timestamp(existing.last_played) or datetime.min)
        ):
            best_scores[snapshot.player_id] = snapshot

    return sorted(
        best_scores.values(),
        key=lambda entry: (entry.score, entry.last_played or datetime.min),
        reverse=True,
    )


def _timeframes(now: datetime) -> list[tuple[str, str, datetime | None]]:
    start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    last_24_hours = now - timedelta(hours=24)

    return [
        ("all-time", "Top all time", None),
        ("year", "Top this year", start_of_year),
        ("month", "Top this month", start_of_month),
        ("week", "Top this week", start_of_week),
        ("24h", "Top last 24 hours", last_24_hours),
    ]


def _build_time_leaderboards(
    snapshots: list[schemas.LeaderboardEntry],
    now: datetime,
    *,
    title_prefix: str | None = None,
    slug_prefix: str | None = None,
    include_empty: bool = False,
) -> list[schemas.TimeWindowLeaderboard]:
    leaderboards: list[schemas.TimeWindowLeaderboard] = []

    for slug, title, since in _timeframes(now):
        entries = _aggregate_by_timeframe(snapshots, since)
        if not entries and not include_empty:
            continue

        leaderboards.append(
            schemas.TimeWindowLeaderboard(
                slug=f"{slug_prefix or ''}{slug}",
                title=f"{title_prefix + ' · ' if title_prefix else ''}{title}",
                since=since,
                leaderboard=entries,
            )
        )

    return leaderboards


def _should_display_tournament(tournament: models.Tournament, now: datetime) -> bool:
    start = _coerce_timestamp(tournament.start_time)
    display_until = _coerce_timestamp(tournament.display_until)

    if tournament.is_active and (start is None or start <= now):
        return True

    if display_until and display_until >= now:
        return True

    # If the admin left the tournament active without dates, show it.
    if (
        tournament.is_active
        and start is None
        and _coerce_timestamp(tournament.end_time) is None
        and display_until is None
    ):
        return True

    return False


def _scoped_template(sql_template: str) -> str:
    sanitized = sql_template.replace(
        "json_each(gs.scores) AS j(player, value)", "json_each(gs.scores) AS j"
    )
    return (
        sanitized.replace("game_states", "scoped_game_states")
        .replace("game_players", "scoped_game_players")
        .replace("games", "scoped_games")
    )


async def _tournament_standings(
    db: AsyncSession, tournament: models.Tournament
) -> list[schemas.TournamentStanding]:
    profile = tournament.scoring_profile
    if not profile:
        return []

    scoped_sql = _scoped_template(profile.sql_template)

    params: dict[str, object] = {}
    game_filters: list[str] = ["1=1"]
    state_filters: list[str] = ["1=1"]
    player_filters: list[str] = ["1=1"]

    if tournament.machines:
        params["machine_ids"] = [link.machine_id for link in tournament.machines]
        game_filters.append("g.machine_id IN :machine_ids")
    if tournament.players:
        params["player_ids"] = [link.player_id for link in tournament.players]
        player_filters.append("gp.player_id IN :player_ids")

    start_time = _coerce_timestamp(tournament.start_time)
    end_time = _coerce_timestamp(tournament.end_time)

    if start_time:
        params["start_time"] = start_time
        state_filters.append("gs.timestamp >= :start_time")
    if end_time:
        params["end_time"] = end_time
        state_filters.append("gs.timestamp <= :end_time")

    game_where = " AND ".join(game_filters)
    state_where = " AND ".join(state_filters)
    player_where = " AND ".join([*game_filters, *player_filters])

    order_direction = "DESC" if profile.sort_direction.lower() != "asc" else "ASC"

    statement = text(
        f"""
        WITH scoped_games AS (
            SELECT * FROM games g
            WHERE {game_where}
        ),
        scoped_game_states AS (
            SELECT gs.*, g.machine_id, g.start_time, g.end_time
            FROM game_states gs
            JOIN scoped_games g ON g.id = gs.game_id
            WHERE {state_where}
        ),
        scoped_game_players AS (
            SELECT gp.*
            FROM game_players gp
            JOIN scoped_games g ON g.id = gp.game_id
            WHERE {player_where}
        ),
        base AS (
            {scoped_sql}
        ),
        last_seen AS (
            SELECT gp.player_id AS player_id, MAX(gs.timestamp) AS last_played
            FROM scoped_game_states gs
            JOIN scoped_game_players gp ON gp.game_id = gs.game_id
            GROUP BY gp.player_id
        )
        SELECT base.player_id AS player_id,
               base.score AS score,
               p.initials AS initials,
               p.screen_name AS screen_name,
               last_seen.last_played AS last_played
        FROM base
        JOIN players p ON p.id = base.player_id
        LEFT JOIN last_seen ON last_seen.player_id = base.player_id
        ORDER BY base.score {order_direction}, (last_played IS NULL), last_played DESC, initials ASC
        LIMIT 10
        """
    )

    if "machine_ids" in params:
        statement = statement.bindparams(bindparam("machine_ids", expanding=True))
    if "player_ids" in params:
        statement = statement.bindparams(bindparam("player_ids", expanding=True))

    result = await db.execute(statement, params)
    rows = result.mappings().all()

    return [
        schemas.TournamentStanding(
            player_id=row.get("player_id"),
            initials=row.get("initials") or "---",
            screen_name=row.get("screen_name"),
            score=int(row.get("score") or 0),
            last_played=_coerce_timestamp(row.get("last_played")),
        )
        for row in rows
    ]


def _tournament_last_activity(
    tournament: models.Tournament, standings: list[schemas.TournamentStanding], now: datetime
) -> Optional[datetime]:
    timestamps: list[datetime | None] = [
        _coerce_timestamp(tournament.updated_at),
        _coerce_timestamp(tournament.end_time),
        _coerce_timestamp(tournament.start_time),
    ]

    latest_standing = max(
        (_coerce_timestamp(entry.last_played) for entry in standings if entry.last_played),
        default=None,
    )
    timestamps.append(latest_standing)

    # Treat an active tournament without records as current activity so it surfaces.
    if tournament.is_active and not any(timestamps):
        timestamps.append(now)

    valid = [ts for ts in timestamps if ts]
    return max(valid) if valid else None


@router.get("/leaderboard", response_model=List[schemas.LeaderboardGame])
async def leaderboard(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(
        select(models.Game)
        .options(
            selectinload(models.Game.machine),
            selectinload(models.Game.game_players).selectinload(models.GamePlayer.player),
            selectinload(models.Game.game_states),
        )
        .order_by(models.Game.id)
    )
    games = result.scalars().unique().all()
    return [_build_leaderboard(game) for game in games]


@router.get("/leaderboard/summary", response_model=schemas.LeaderboardSummary)
async def leaderboard_summary(
    db: AsyncSession = Depends(database.get_db),
    offset: int = Query(0, ge=0),
    limit: int | None = Query(None, ge=1),
):
    result = await db.execute(
        select(models.Game)
        .options(
            selectinload(models.Game.machine),
            selectinload(models.Game.game_players).selectinload(models.GamePlayer.player),
            selectinload(models.Game.game_states),
        )
        .order_by(models.Game.id)
    )
    games = result.scalars().unique().all()
    now = datetime.now(timezone.utc)
    leaderboards: list[schemas.TimeWindowLeaderboard] = []
    grouped_games: list[schemas.GameLeaderboardBundle] = []
    for game in games:
        windows = _build_time_leaderboards(
            _player_snapshots([game]),
            now,
            title_prefix=game.machine.name if game.machine else "Unknown game",
            slug_prefix=f"game-{game.id}-",
            include_empty=True,
        )

        champion = None
        if windows and windows[0].leaderboard:
            champion = windows[0].leaderboard[0]

        last_activity = _game_last_activity(game)

        grouped_games.append(
            schemas.GameLeaderboardBundle(
                id=game.id,
                machine_name=game.machine.name if game.machine else "Unknown game",
                is_active=game.is_active,
                windows=windows,
                champion=champion,
                last_activity_at=last_activity,
            )
        )

        leaderboards.extend(windows)

    total = len(leaderboards)

    if limit is not None and total:
        end = min(offset + limit, total)
        if offset >= total:
            offset = 0
            end = min(limit, total)
        leaderboards = leaderboards[offset:end]
    elif limit is not None:
        leaderboards = []

    tournament_result = await db.execute(
        select(models.Tournament)
        .options(
            selectinload(models.Tournament.scoring_profile),
            selectinload(models.Tournament.game_mode),
            selectinload(models.Tournament.machines),
            selectinload(models.Tournament.players),
        )
        .order_by(models.Tournament.start_time)
    )

    tournaments: list[schemas.TournamentBoard] = []
    for tournament in tournament_result.scalars().unique().all():
        if not _should_display_tournament(tournament, now):
            continue

        standings = await _tournament_standings(db, tournament)
        activity = _tournament_last_activity(tournament, standings, now)
        tournaments.append(
            schemas.TournamentBoard(
                id=tournament.id,
                name=tournament.name,
                slug=tournament.slug,
                description=tournament.description,
                start_time=tournament.start_time,
                end_time=tournament.end_time,
                display_until=tournament.display_until,
                is_active=tournament.is_active,
                scoring_profile=tournament.scoring_profile,
                game_mode=tournament.game_mode,
                leaderboard=standings,
                last_activity_at=activity,
            )
        )

    return schemas.LeaderboardSummary(
        games=grouped_games,
        leaderboards=leaderboards,
        total_boards=total,
        tournaments=tournaments,
    )
