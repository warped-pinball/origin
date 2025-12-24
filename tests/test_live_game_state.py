import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin")

sys.path.append("/workspace/the-box")

from api_app.main import app  # noqa: E402
from api_app import database, models, udp  # noqa: E402
from api_app.database import Base, engine  # noqa: E402


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _create_game_with_states(
    session: database.AsyncSessionLocal,
    *,
    uid: str,
    name: str = "Test Machine",
    states: list[dict],
    players: list[tuple[str, str]] | None = None,
):
    machine = models.Machine(
        name=name,
        uid=uid,
        ip_address="192.0.2.10",
        last_seen=datetime.now(timezone.utc),
    )
    game = models.Game(machine=machine, is_active=True)

    game_players = []
    if players:
        for idx, (initials, screen_name) in enumerate(players, start=1):
            player = models.Player(
                initials=initials,
                screen_name=screen_name,
                email=f"{initials.lower()}@example.com",
            )
            game_player = models.GamePlayer(game=game, player=player, player_number=idx)
            game_players.append(game_player)

    game_states = [models.GameState(game=game, **state) for state in states]

    session.add_all([machine, game, *game_players, *game_states])
    await session.commit()
    await session.refresh(game)
    return game


@pytest.mark.asyncio
async def test_live_games_returns_latest_state(async_client):
    async with database.AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        game = await _create_game_with_states(
            session,
            uid="test-uid",
            players=[("AAA", "Player One"), ("BBB", "Player Two")],
            states=[
                {
                    "seconds_elapsed": 30,
                    "ball": 1,
                    "player_up": 1,
                    "scores": {"1": 1000, "2": 500},
                    "timestamp": now - timedelta(minutes=5),
                },
                {
                    "seconds_elapsed": 95,
                    "ball": 2,
                    "player_up": 2,
                    "scores": {"1": 1200, "2": 3200},
                    "timestamp": now,
                },
            ],
        )

    response = await async_client.get("/api/v1/games/live")
    assert response.status_code == 200

    payload = response.json()
    assert len(payload) == 1
    game_state = payload[0]

    assert game_state["game_id"] == game.id
    assert game_state["ball"] == 2
    assert game_state["player_up"] == 2
    assert game_state["seconds_elapsed"] == 95
    assert len(game_state["scores"]) == 2
    assert game_state["scores"][0]["score"] == 1200
    assert game_state["scores"][1]["score"] == 3200
    assert game_state["scores"][0]["ball_times"] == [
        {"ball": 1, "seconds": 0, "score": 0, "is_current": False},
        {"ball": 2, "seconds": 0, "score": 200, "is_current": False},
    ]
    assert game_state["scores"][1]["ball_times"] == [
        {"ball": 2, "seconds": 0, "score": 2700, "is_current": True},
    ]
    assert game_state["scores"][1]["is_player_up"] is True


@pytest.mark.asyncio
async def test_live_game_endpoint_filters_by_id(async_client):
    async with database.AsyncSessionLocal() as session:
        game = await _create_game_with_states(
            session,
            uid="test-uid",
            players=[("AAA", "Player One")],
            states=[
                {
                    "seconds_elapsed": 30,
                    "ball": 1,
                    "player_up": 1,
                    "scores": {"1": 1000},
                    "timestamp": datetime.now(timezone.utc),
                }
            ],
        )

    response = await async_client.get(f"/api/v1/games/{game.id}/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["machine_uid"] == "test-uid"

    missing = await async_client.get("/api/v1/games/999/live")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_live_games_skip_stale_states(async_client):
    async with database.AsyncSessionLocal() as session:
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        active_time = datetime.now(timezone.utc)

        await _create_game_with_states(
            session,
            uid="stale-uid",
            players=[("OLD", "Old Player")],
            states=[
                {
                    "seconds_elapsed": 5,
                    "ball": 1,
                    "player_up": 1,
                    "scores": {"1": 100},
                    "timestamp": stale_time,
                }
            ],
        )

        await _create_game_with_states(
            session,
            uid="active-uid",
            states=[
                {
                    "seconds_elapsed": 12,
                    "ball": 1,
                    "player_up": 1,
                    "scores": [5000, 0],
                    "timestamp": active_time - timedelta(seconds=10),
                },
                {
                    "seconds_elapsed": 26,
                    "ball": 1,
                    "player_up": 1,
                    "scores": [12500, 0],
                    "timestamp": active_time,
                },
            ],
            players=None,
        )

    response = await async_client.get("/api/v1/games/live")
    assert response.status_code == 200

    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["machine_uid"] == "active-uid"
    assert payload[0]["scores"][0]["score"] == 12500
    assert payload[0]["scores"][0]["is_player_up"] is True


@pytest.mark.asyncio
async def test_live_games_report_play_durations(async_client):
    async with database.AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        await _create_game_with_states(
            session,
            uid="timing-uid",
            players=None,
            states=[
                {
                    "seconds_elapsed": 10,
                    "ball": 1,
                    "player_up": 1,
                    "scores": [1000, 0, 0, 0],
                    "timestamp": now - timedelta(seconds=50),
                },
                {
                    "seconds_elapsed": 25,
                    "ball": 1,
                    "player_up": 1,
                    "scores": [2500, 0, 0, 0],
                    "timestamp": now - timedelta(seconds=25),
                },
                {
                    "seconds_elapsed": 45,
                    "ball": 2,
                    "player_up": 1,
                    "scores": [3000, 0, 0, 0],
                    "timestamp": now - timedelta(seconds=10),
                },
                {
                    "seconds_elapsed": 65,
                    "ball": 2,
                    "player_up": 1,
                    "scores": [4500, 0, 0, 0],
                    "timestamp": now,
                },
            ],
        )

    response = await async_client.get("/api/v1/games/live")
    assert response.status_code == 200

    payload = response.json()
    assert len(payload) == 1
    entry = payload[0]["scores"][0]
    assert entry["player_number"] == 1
    assert entry["score"] == 4500
    assert entry["ball_times"] == [
        {"ball": 1, "seconds": 15, "score": 1500, "is_current": False},
        {"ball": 2, "seconds": 20, "score": 2000, "is_current": True},
    ]
    assert entry["is_player_up"] is True


@pytest.mark.asyncio
async def test_live_games_track_per_player_ball_times(async_client):
    async with database.AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        await _create_game_with_states(
            session,
            uid="ball-times",
            players=None,
            states=[
                {
                    "seconds_elapsed": 5,
                    "ball": 1,
                    "player_up": 1,
                    "scores": [100, 0],
                    "timestamp": now - timedelta(seconds=40),
                },
                {
                    "seconds_elapsed": 25,
                    "ball": 1,
                    "player_up": 1,
                    "scores": [500, 0],
                    "timestamp": now - timedelta(seconds=20),
                },
                {
                    "seconds_elapsed": 40,
                    "ball": 1,
                    "player_up": 2,
                    "scores": [500, 200],
                    "timestamp": now - timedelta(seconds=10),
                },
                {
                    "seconds_elapsed": 70,
                    "ball": 1,
                    "player_up": 2,
                    "scores": [500, 700],
                    "timestamp": now,
                },
            ],
        )

    response = await async_client.get("/api/v1/games/live")
    assert response.status_code == 200

    payload = response.json()
    assert len(payload) == 1
    scores = payload[0]["scores"]

    p1 = next(entry for entry in scores if entry["player_number"] == 1)
    p2 = next(entry for entry in scores if entry["player_number"] == 2)

    assert p1["ball_times"] == [
        {"ball": 1, "seconds": 20, "score": 400, "is_current": False}
    ]
    assert p2["ball_times"] == [
        {"ball": 1, "seconds": 30, "score": 700, "is_current": True}
    ]


@pytest.mark.asyncio
async def test_live_games_capture_multiple_players_without_player_up(async_client):
    async with database.AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        await _create_game_with_states(
            session,
            uid="no-player-up",
            players=None,
            states=[
                {
                    "seconds_elapsed": 5,
                    "ball": 1,
                    "player_up": 1,
                    "scores": [100, 0],
                    "timestamp": now - timedelta(seconds=40),
                },
                {
                    "seconds_elapsed": 15,
                    "ball": 1,
                    "player_up": 1,
                    "scores": [500, 0],
                    "timestamp": now - timedelta(seconds=30),
                },
                {
                    "seconds_elapsed": 30,
                    "ball": 1,
                    "player_up": 1,
                    "scores": [500, 700],
                    "timestamp": now - timedelta(seconds=15),
                },
                {
                    "seconds_elapsed": 50,
                    "ball": 1,
                    "player_up": 1,
                    "scores": [500, 1_700],
                    "timestamp": now,
                },
            ],
        )

    response = await async_client.get("/api/v1/games/live")
    assert response.status_code == 200

    payload = response.json()
    assert len(payload) == 1
    scores = payload[0]["scores"]

    assert len(scores) == 2
    p1 = next(entry for entry in scores if entry["player_number"] == 1)
    p2 = next(entry for entry in scores if entry["player_number"] == 2)

    assert p1["ball_times"] == [
        {"ball": 1, "seconds": 10, "score": 400, "is_current": False}
    ]
    assert p2["ball_times"] == [
        {"ball": 1, "seconds": 20, "score": 1_700, "is_current": True}
    ]
    assert p2["is_player_up"] is True


@pytest.mark.asyncio
async def test_live_games_track_last_scorer(async_client):
    async with database.AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        await _create_game_with_states(
            session,
            uid="who-rolled",  # noqa: S608 - not user input
            players=[("P1A", "Player One"), ("P2B", "Player Two")],
            states=[
                {
                    "seconds_elapsed": 3,
                    "ball": 1,
                    "player_up": 1,
                    "scores": {"1": 1_000, "2": 0},
                    "timestamp": now - timedelta(seconds=20),
                },
                {
                    "seconds_elapsed": 10,
                    "ball": 1,
                    "player_up": 2,
                    "scores": {"1": 1_200, "2": 2_500},
                    "timestamp": now - timedelta(seconds=10),
                },
                {
                    "seconds_elapsed": 18,
                    "ball": 1,
                    "player_up": 1,
                    "scores": {"1": 1_200, "2": 5_500},
                    "timestamp": now,
                },
            ],
        )

    response = await async_client.get("/api/v1/games/live")
    assert response.status_code == 200

    payload = response.json()
    assert payload[0]["player_up"] == 2
    scores = payload[0]["scores"]
    p2 = next(score for score in scores if score["player_number"] == 2)
    assert p2["is_player_up"] is True
    p1 = next(score for score in scores if score["player_number"] == 1)
    assert p1["is_player_up"] is False


@pytest.mark.asyncio
async def test_game_state_preserves_named_machine(async_client):
    async with database.AsyncSessionLocal() as session:
        machine = models.Machine(
            name="Grand Prix",
            uid="keep-name",
            ip_address="198.51.100.8",
            last_seen=datetime.now(timezone.utc),
        )
        game = models.Game(machine=machine, is_active=True)
        session.add_all([machine, game])
        await session.commit()

    await udp._handle_game_state_message(
        {
            "machine_id": "keep-name",
            "gameTimeMs": 10_000,
            "scores": [5_000, 1_200],
            "ball_in_play": 2,
            "player_up": 1,
            "game_active": True,
        },
        "198.51.100.8",
    )

    async with database.AsyncSessionLocal() as session:
        refreshed = await session.get(models.Machine, machine.id)
        assert refreshed.name == "Grand Prix"

        state_query = await session.execute(
            select(models.GameState).where(models.GameState.game_id == game.id)
        )
        saved_state = state_query.scalars().first()
        assert saved_state is not None

    response = await async_client.get("/api/v1/games/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload and payload[0]["machine_name"] == "Grand Prix"


@pytest.mark.asyncio
async def test_ingest_game_state_prefers_reported_ip(monkeypatch):
    async def fake_version(ip_address, attempts=2):
        return None

    monkeypatch.setattr(udp, "_fetch_machine_version", fake_version)

    async with database.AsyncSessionLocal() as session:
        await udp.ingest_game_state(
            session,
            {
                "machine_id": "ray-123",
                "machine_name": "Signal Runner",
                "machine_ip": "10.1.1.50",
                "game_active": True,
                "scores": {"1": 1000},
            },
            "172.19.0.1",
        )

    async with database.AsyncSessionLocal() as session:
        machine_query = await session.execute(select(models.Machine))
        machine = machine_query.scalars().first()

        assert machine is not None
        assert machine.ip_address == "10.1.1.50"
        assert machine.name == "Signal Runner"
