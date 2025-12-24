from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models


async def _existing_records(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(models.Game.id)))
    return int(result.scalar_one())


async def _existing_tournaments(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(models.Tournament.id)))
    return int(result.scalar_one())


def _player_payloads() -> list[dict]:
    return [
        {"initials": "WIZ", "first_name": "Willa", "last_name": "Zane", "email": "willa@example.com", "screen_name": "Wizard"},
        {"initials": "NIN", "first_name": "Noel", "last_name": "Indigo", "email": "noel@example.com", "screen_name": "NinjaCat"},
        {"initials": "BOT", "first_name": "Bowie", "last_name": "Tanner", "email": "bowie@example.com", "screen_name": "BotMaster"},
        {"initials": "SKY", "first_name": "Sky", "last_name": "Ramirez", "email": "sky@example.com", "screen_name": "Skyline"},
        {"initials": "GAL", "first_name": "Gale", "last_name": "Lumen", "email": "gale@example.com", "screen_name": "Galeforce"},
        {"initials": "LUX", "first_name": "Lux", "last_name": "Keller", "email": "lux@example.com", "screen_name": "Luxor"},
        {"initials": "ARC", "first_name": "Archer", "last_name": "Cole", "email": "archer@example.com", "screen_name": "Archlight"},
        {"initials": "ZEN", "first_name": "Zenia", "last_name": "Noor", "email": "zenia@example.com", "screen_name": "Zenith"},
    ]


def _machine_payloads() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "name": "Nebula Orbit",
            "ip_address": "10.0.0.21",
            "uid": "machine-nebula",
            "last_seen": now,
        },
        {
            "name": "Gravity Well",
            "ip_address": "10.0.0.22",
            "uid": "machine-gravity",
            "last_seen": now,
        },
        {
            "name": "Solar Flare",
            "ip_address": "10.0.0.23",
            "uid": "machine-solar",
            "last_seen": now,
        },
    ]


def _attach_players_to_game(game: models.Game, players: Iterable[models.Player]) -> list[models.GamePlayer]:
    return [
        models.GamePlayer(game=game, player=player, player_number=idx + 1)
        for idx, player in enumerate(players)
    ]


def _build_states(
    game: models.Game,
    base_time: datetime,
    score_snapshots: Sequence[dict],
    spacing_minutes: int = 6,
) -> list[models.GameState]:
    return [
        models.GameState(
            game=game,
            seconds_elapsed=spacing_minutes * 60 * (idx + 1),
            ball=idx + 1,
            player_up=(idx % len(snapshot)) + 1,
            scores=snapshot,
            timestamp=base_time + timedelta(minutes=idx * spacing_minutes),
        )
        for idx, snapshot in enumerate(score_snapshots)
    ]


def _create_game(
    machine: models.Machine,
    players: Sequence[models.Player],
    start_time: datetime,
    is_active: bool,
) -> models.Game:
    end_time = None if is_active else start_time + timedelta(minutes=50)
    return models.Game(machine=machine, is_active=is_active, start_time=start_time, end_time=end_time)


async def _ensure_game_modes(session: AsyncSession) -> dict[str, models.GameMode]:
    result = await session.execute(select(models.GameMode))
    existing = {mode.slug: mode for mode in result.scalars().all()}
    defaults = [
        {
            "name": "Standard Play",
            "slug": "standard",
            "description": "Default behavior with no special tournament constraints.",
        },
        {
            "name": "Pin Golf",
            "slug": "pin-golf",
            "description": "Players aim for the target and score is measured by balls used.",
            "activation_payload": {"mode": "pin_golf"},
        },
    ]

    for payload in defaults:
        if payload["slug"] not in existing:
            mode = models.GameMode(**payload)
            session.add(mode)
            existing[payload["slug"]] = mode
    await session.flush()
    return existing


async def _ensure_leaderboard_profiles(session: AsyncSession) -> dict[str, models.LeaderboardProfile]:
    result = await session.execute(select(models.LeaderboardProfile))
    existing = {profile.slug: profile for profile in result.scalars().all()}
    defaults = [
        {
            "name": "High Score",
            "slug": "high-score",
            "description": "Traditional leaderboard sorted by max score.",
            "sql_template": """SELECT gp.player_id, MAX(value) AS score FROM game_states gs CROSS JOIN json_each(gs.scores) AS j JOIN game_players gp ON gp.game_id = gs.game_id AND gp.player_number = j.key GROUP BY gp.player_id""",
            "sort_direction": "desc",
        },
        {
            "name": "Limbo",
            "slug": "limbo",
            "description": "Lowest score wins for the set of eligible games.",
            "sql_template": """SELECT gp.player_id, MIN(value) AS score FROM game_states gs CROSS JOIN json_each(gs.scores) AS j JOIN game_players gp ON gp.game_id = gs.game_id AND gp.player_number = j.key GROUP BY gp.player_id""",
            "sort_direction": "asc",
        },
    ]

    for payload in defaults:
        stored = existing.get(payload["slug"])
        if stored:
            stored.name = payload["name"]
            stored.description = payload["description"]
            stored.sql_template = payload["sql_template"]
            stored.sort_direction = payload["sort_direction"]
        else:
            profile = models.LeaderboardProfile(**payload)
            session.add(profile)
            existing[payload["slug"]] = profile
    await session.flush()
    return existing


async def _maybe_create_demo_tournaments(
    session: AsyncSession,
    machines: Sequence[models.Machine],
    players: Sequence[models.Player],
    profiles: dict[str, models.LeaderboardProfile],
    modes: dict[str, models.GameMode],
    time_marks: dict[str, datetime],
):
    if await _existing_tournaments(session):
        return

    tournament = models.Tournament(
        name="Limbo Weekend",
        slug="limbo-weekend",
        description="Lowest score across featured games from Friday midnight to Sunday night.",
        scoring_profile=profiles.get("limbo"),
        game_mode=modes.get("pin-golf"),
        start_time=time_marks["week"],
        end_time=time_marks["recent"],
        display_until=time_marks["recent"] + timedelta(hours=4),
        is_active=False,
    )

    tournament.machines = [models.TournamentMachine(machine=machine) for machine in machines[:2]]
    tournament.players = [models.TournamentPlayer(player=player) for player in players[:4]]

    session.add(tournament)


async def seed_example_data(session: AsyncSession) -> None:
    """Populate the database with predictable demo content.

    The seed runs only when no games exist to avoid clobbering real data.
    """

    if await _existing_records(session):
        return

    players = [models.Player(**payload) for payload in _player_payloads()]
    machines = [models.Machine(**payload) for payload in _machine_payloads()]

    session.add_all([*players, *machines])
    await session.flush()

    modes = await _ensure_game_modes(session)
    profiles = await _ensure_leaderboard_profiles(session)

    now = datetime.now(timezone.utc)
    time_marks = {
        "recent": now - timedelta(hours=2),
        "week": now - timedelta(days=3),
        "month": now - timedelta(days=18),
        "year": now - timedelta(days=180),
        "archive": now - timedelta(days=420),
    }

    game_specs = [
        {
            "machine": machines[0],
            "players": players[:3],
            "start": time_marks["recent"],
            "is_active": True,
            "snapshots": [
                {"1": 325_000, "2": 287_500, "3": 192_000},
                {"1": 612_000, "2": 555_000, "3": 404_000},
                {"1": 1_240_000, "2": 1_050_000, "3": 866_000},
            ],
            "spacing": 4,
        },
        {
            "machine": machines[1],
            "players": players[2:5],
            "start": time_marks["week"],
            "is_active": False,
            "snapshots": [
                {"1": 220_000, "2": 184_000, "3": 92_000},
                {"1": 522_500, "2": 610_250, "3": 221_000},
                {"1": 811_400, "2": 1_202_000, "3": 644_500},
            ],
            "spacing": 6,
        },
        {
            "machine": machines[2],
            "players": [players[1], players[3], players[5], players[7]],
            "start": time_marks["month"],
            "is_active": False,
            "snapshots": [
                {"1": 980_000_000, "2": 750_000_000, "3": 1_120_000_000, "4": 640_000_000},
                {"1": 1_360_000_000, "2": 1_240_000_000, "3": 1_880_000_000, "4": 890_000_000},
                {"1": 1_760_000_000_000, "2": 1_025_000_000_000, "3": 2_240_000_000_000, "4": 250_000_000_000},
            ],
            "spacing": 8,
        },
        {
            "machine": machines[0],
            "players": [players[0], players[4], players[6]],
            "start": time_marks["year"],
            "is_active": False,
            "snapshots": [
                {"1": 1_050_000, "2": 1_240_000, "3": 995_000},
                {"1": 1_540_000, "2": 1_760_000, "3": 1_420_000},
            ],
            "spacing": 10,
        },
        {
            "machine": machines[1],
            "players": [players[1], players[2], players[7]],
            "start": time_marks["archive"],
            "is_active": False,
            "snapshots": [
                {"1": 320_000, "2": 280_000, "3": 360_000},
                {"1": 880_000, "2": 940_000, "3": 1_050_000},
            ],
            "spacing": 12,
        },
    ]

    for spec in game_specs:
        game = _create_game(spec["machine"], spec["players"], spec["start"], spec["is_active"])
        session.add(game)
        await session.flush()

        session.add_all(_attach_players_to_game(game, spec["players"]))
        state_base = spec["start"] + timedelta(minutes=8)
        states = _build_states(
            game,
            state_base,
            spec["snapshots"],
            spacing_minutes=spec.get("spacing", 6),
        )

        if spec["is_active"] and states:
            states[-1].timestamp = datetime.now(timezone.utc) - timedelta(seconds=20)

        session.add_all(states)

    await _maybe_create_demo_tournaments(session, machines, players, profiles, modes, time_marks)

    await session.commit()
