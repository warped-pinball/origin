import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from .. import models
from ..crud.dashboard import get_location_scoreboard_version
from ..routers.scoreboard import _location_scoreboard_stream


def create_user(db_session, *, email: str | None = None, screen_name: str | None = None):
    if email is None:
        email = f"{uuid4().hex}@example.com"
    if screen_name is None:
        screen_name = f"Player{uuid4().hex[:6]}"
    user = models.User(
        email=email,
        hashed_password="hashed",
        screen_name=screen_name,
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_scoreboard_returns_recent_state_and_high_scores(client, db_session):
    user = create_user(db_session, email="score@example.com", screen_name="ScoreMaster")
    location = models.Location(user_id=user.id, name="Downtown Arcade")
    db_session.add(location)
    db_session.flush()

    machine = models.Machine(
        id="machine-1",
        shared_secret="secret",
        user_id=user.id,
        location_id=location.id,
        game_title="Galaxy Quest",
    )
    db_session.add(machine)

    now = datetime.utcnow()

    scores = [
        models.Score(
            user_id=user.id,
            machine_id=machine.id,
            game="Galaxy Quest",
            value=120000,
            created_at=now - timedelta(hours=5),
        ),
        models.Score(
            user_id=user.id,
            machine_id=machine.id,
            game="Galaxy Quest",
            value=90000,
            created_at=now - timedelta(days=5),
        ),
        models.Score(
            user_id=user.id,
            machine_id=machine.id,
            game="Galaxy Quest",
            value=45000,
            created_at=now - timedelta(days=45),
        ),
    ]

    db_session.add_all(scores)

    state = models.MachineGameState(
        machine_id=machine.id,
        time_ms=185000,
        ball_in_play=2,
        scores=[32000, 28500],
        player_up=1,
        players_total=2,
        created_at=now,
        game_active=True,
    )
    db_session.add(state)
    db_session.commit()

    response = client.get(f"/api/v1/public/locations/{location.id}/scoreboard")
    assert response.status_code == 200
    payload = response.json()

    assert payload["location_id"] == location.id
    assert payload["location_name"] == "Downtown Arcade"
    assert payload["machines"], "Expected at least one machine payload"

    machine_payload = payload["machines"][0]
    assert machine_payload["machine_id"] == machine.id
    assert machine_payload["is_active"] is True
    assert machine_payload["scores"] == [32000, 28500]

    all_time = machine_payload["high_scores"]["all_time"]
    daily = machine_payload["high_scores"]["daily"]
    monthly = machine_payload["high_scores"]["monthly"]

    assert [entry["value"] for entry in all_time] == [120000, 90000, 45000]
    assert [entry["value"] for entry in monthly] == [120000, 90000]
    assert [entry["value"] for entry in daily] == [120000]

    assert all(entry["player_name"] == "ScoreMaster" for entry in all_time)
    assert all(entry["duration_ms"] is None for entry in all_time)


def test_scoreboard_returns_404_for_unknown_location(client):
    response = client.get("/api/v1/public/locations/999/scoreboard")
    assert response.status_code == 404
    assert response.json()["detail"] == "Location not found"


def test_location_display_page_renders_for_existing_location(client, db_session):
    user = create_user(db_session)
    location = models.Location(user_id=user.id, name="Uptown Arcade")
    db_session.add(location)
    db_session.commit()

    response = client.get(f"/locations/{location.id}/display")
    assert response.status_code == 200
    assert "Uptown Arcade" in response.text
    assert "data-count-up" in response.text


def test_get_location_scoreboard_version_tracks_latest_activity(db_session):
    user = create_user(db_session)
    location = models.Location(user_id=user.id, name="Westside Arcade")
    db_session.add(location)
    db_session.flush()

    machine = models.Machine(
        id="machine-track",
        user_id=user.id,
        shared_secret=f"secret-{uuid4().hex}",
        location_id=location.id,
        game_title="Tracker",
    )
    db_session.add(machine)
    db_session.commit()

    assert get_location_scoreboard_version(db_session, location.id) is None

    earlier = datetime.utcnow().replace(microsecond=0) - timedelta(minutes=5)
    state = models.MachineGameState(
        machine_id=machine.id,
        time_ms=1000,
        scores=[1000],
        ball_in_play=1,
        player_up=0,
        players_total=1,
        created_at=earlier,
        game_active=True,
    )
    db_session.add(state)
    db_session.commit()

    version_after_state = get_location_scoreboard_version(db_session, location.id)
    assert version_after_state == earlier

    later = datetime.utcnow().replace(microsecond=0)
    score = models.Score(
        user_id=user.id,
        machine_id=machine.id,
        game="Tracker",
        value=12345,
        created_at=later,
    )
    db_session.add(score)
    db_session.commit()

    version_after_score = get_location_scoreboard_version(db_session, location.id)
    assert version_after_score == later


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_scoreboard_stream_emits_events_for_updates(db_session, anyio_backend):
    user = create_user(db_session)
    location = models.Location(user_id=user.id, name="Stream Arcade")
    db_session.add(location)
    db_session.flush()

    machine = models.Machine(
        id="machine-stream",
        shared_secret=f"secret-{uuid4().hex}",
        user_id=user.id,
        location_id=location.id,
        game_title="Streamer",
    )
    db_session.add(machine)
    db_session.commit()

    first_timestamp = datetime.utcnow().replace(microsecond=0)
    initial_state = models.MachineGameState(
        machine_id=machine.id,
        time_ms=500,
        scores=[1000],
        ball_in_play=1,
        player_up=0,
        players_total=1,
        created_at=first_timestamp,
        game_active=True,
    )
    db_session.add(initial_state)
    db_session.commit()

    class StubRequest:
        def __init__(self) -> None:
            self._disconnected = False

        async def is_disconnected(self) -> bool:
            return self._disconnected

        def disconnect(self) -> None:
            self._disconnected = True

    request = StubRequest()
    generator = _location_scoreboard_stream(location.id, request, 0.05)

    first_event = await asyncio.wait_for(generator.__anext__(), timeout=2.0)
    assert first_timestamp.isoformat() in first_event

    second_timestamp = first_timestamp + timedelta(minutes=1)
    next_state = models.MachineGameState(
        machine_id=machine.id,
        time_ms=750,
        scores=[2000],
        ball_in_play=1,
        player_up=0,
        players_total=1,
        created_at=second_timestamp,
        game_active=True,
    )
    db_session.add(next_state)
    db_session.commit()

    second_event = await asyncio.wait_for(generator.__anext__(), timeout=2.0)
    assert second_timestamp.isoformat() in second_event

    request.disconnect()
    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(generator.__anext__(), timeout=1.0)
