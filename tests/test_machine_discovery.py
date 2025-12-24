import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
import httpx
from sqlalchemy import select, func

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin")

sys.path.append("/workspace/the-box")

from api_app import database, models, udp  # noqa: E402
from api_app.database import Base, engine  # noqa: E402


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    await database.init_db()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def clear_uid_cache():
    udp._uid_fetch_cache.clear()
    yield
    udp._uid_fetch_cache.clear()


@pytest.mark.asyncio
async def test_upsert_updates_ip_for_same_uid_and_name(monkeypatch):
    monkeypatch.setattr(udp, "_fetch_machine_uid", AsyncMock(return_value="uid-fixed"))

    async with database.AsyncSessionLocal() as session:
        first = await udp._upsert_machine(session, "192.168.0.10", "Orbiter", commit=False)
        await session.commit()

        updated = await udp._upsert_machine(session, "192.168.0.11", "Orbiter", commit=False)
        await session.commit()

        assert first.id == updated.id
        assert updated.ip_address == "192.168.0.11"


@pytest.mark.asyncio
async def test_upsert_creates_new_machine_for_new_name_with_same_uid(monkeypatch):
    monkeypatch.setattr(udp, "_fetch_machine_uid", AsyncMock(return_value="uid-fixed"))

    async with database.AsyncSessionLocal() as session:
        original = await udp._upsert_machine(session, "192.168.0.20", "Starlight", commit=False)
        await session.commit()

        replacement = await udp._upsert_machine(session, "192.168.0.21", "Nebula", commit=False)
        await session.commit()

        assert original.id == replacement.id
        assert replacement.name == "Nebula"
        assert replacement.ip_address == "192.168.0.21"

        result = await session.execute(select(models.Machine).where(models.Machine.uid == "uid-fixed"))
        machines = result.scalars().all()
        assert len(machines) == 1


@pytest.mark.asyncio
async def test_upsert_skips_machine_without_uid(monkeypatch):
    monkeypatch.setattr(udp, "_fetch_machine_uid", AsyncMock(return_value=None))

    async with database.AsyncSessionLocal() as session:
        baseline = await session.execute(select(func.count(models.Machine.id)))
        existing_count = baseline.scalar_one()
        machine = await udp._upsert_machine(session, "192.168.0.30", "Phantom", commit=False)
        await session.commit()

        assert machine is None
        result = await session.execute(select(func.count(models.Machine.id)))
        assert result.scalar_one() == existing_count


@pytest.mark.asyncio
async def test_fetch_machine_uid_retries_and_succeeds(monkeypatch):
    attempts = []

    class DummyResponse:
        def __init__(self, status_code, payload=None, exc=None):
            self.status_code = status_code
            self._payload = payload or {}
            self._exc = exc
            self.headers = {"content-type": "application/json"}

        def raise_for_status(self):
            if self._exc:
                raise self._exc

        def json(self):
            return self._payload

    class DummyClient:
        def __init__(self, responses):
            self._responses = responses

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            attempts.append(url)
            response = self._responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

    responses = [
        httpx.ConnectError("boom"),
        DummyResponse(200, payload={}),
        DummyResponse(200, payload={"uid": "uid-success"}),
    ]

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: DummyClient(responses))

    uid = await udp._fetch_machine_uid("192.168.10.10", attempts=3)

    assert uid == "uid-success"
    assert len(attempts) == 3


@pytest.mark.asyncio
async def test_fetch_machine_uid_gives_up_after_attempts(monkeypatch):
    class DummyResponse:
        def __init__(self, status_code, payload=None, exc=None):
            self.status_code = status_code
            self._payload = payload or {}
            self._exc = exc
            self.headers = {"content-type": "application/json"}

        def raise_for_status(self):
            if self._exc:
                raise self._exc

        def json(self):
            return self._payload

    class DummyClient:
        def __init__(self, responses):
            self._responses = responses

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            response = self._responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

    responses = [httpx.ConnectError("boom"), httpx.ConnectError("boom"), httpx.ReadTimeout("timeout")]
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: DummyClient(responses))

    uid = await udp._fetch_machine_uid("192.168.10.20", attempts=3)

    assert uid is None


@pytest.mark.asyncio
async def test_fetch_machine_uid_throttles_after_failure(monkeypatch):
    attempts = 0
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            nonlocal attempts
            attempts += 1
            raise httpx.ConnectError("boom")

    def fake_now():
        return now

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: DummyClient())
    monkeypatch.setattr(udp, "_utcnow", fake_now)

    uid = await udp._fetch_machine_uid("192.168.50.50")

    assert uid is None
    assert attempts == 2

    # Subsequent call within cooldown should not trigger new HTTP attempts
    uid_again = await udp._fetch_machine_uid("192.168.50.50")
    assert uid_again is None
    assert attempts == 2

    # Advance past cooldown and ensure attempts resume
    now += timedelta(seconds=udp.UID_FETCH_FAILURE_COOLDOWN_SECONDS + 1)
    uid_final = await udp._fetch_machine_uid("192.168.50.50")

    assert uid_final is None
    assert attempts == 4


@pytest.mark.asyncio
async def test_ingest_game_state_serializes_by_machine(monkeypatch):
    monkeypatch.setattr(udp, "_maybe_refresh_version", AsyncMock())

    async def send_state():
        async with database.AsyncSessionLocal() as session:
            await udp.ingest_game_state(
                session,
                {
                    "machine_id": "lock-uid",
                    "scores": {"1": 1000},
                    "gameTimeMs": 1000,
                    "ball_in_play": 1,
                    "player_up": 1,
                },
                "203.0.113.10",
            )

    await asyncio.gather(send_state(), send_state())

    async with database.AsyncSessionLocal() as session:
        machines = (
            await session.execute(
                select(models.Machine).where(models.Machine.uid == "lock-uid")
            )
        ).scalars().all()
        assert len(machines) == 1

        games = (
            await session.execute(
                select(models.Game).where(models.Game.machine_id == machines[0].id)
            )
        ).scalars().all()
        states = (
            await session.execute(
                select(models.GameState).where(models.GameState.game_id == games[0].id)
            )
        ).scalars().all()

    assert len(games) == 1
    assert len(states) == 2
