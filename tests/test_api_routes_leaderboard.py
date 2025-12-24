import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from api_app import database  # noqa: E402
from api_app.database import Base, engine  # noqa: E402
from api_app.main import app  # noqa: E402


@pytest_asyncio.fixture(scope="function")
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await database.init_db()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_leaderboard_summary_has_one_tournament(async_client):
    response = await async_client.get("/api/v1/leaderboard/summary")
    assert response.status_code == 200

    payload = response.json()
    assert payload["tournaments"], "expected tournaments in summary payload"
    assert len(payload["tournaments"]) == 1
    assert payload["tournaments"][0]["name"] == "Limbo Weekend"

    total_windows = sum(len(game.get("windows", [])) for game in payload.get("games", []))
    assert total_windows > 0
    assert any(game.get("champion") for game in payload.get("games", []))


@pytest.mark.asyncio
async def test_live_games_surface_seeded_activity(async_client):
    response = await async_client.get("/api/v1/games/live")
    assert response.status_code == 200

    payload = response.json()
    assert payload, "seed data should provide at least one live game"

    live_game = payload[0]
    assert live_game["machine_name"] == "Nebula Orbit"
    assert live_game["scores"], "live scores should include player entries"
    assert any(score["is_player_up"] for score in live_game["scores"])
