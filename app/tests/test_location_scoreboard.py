from datetime import datetime, timedelta
from uuid import uuid4

from .. import models


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


def test_scoreboard_includes_scores_from_game_end(client, db_session):
    user = create_user(db_session)
    location = models.Location(user_id=user.id, name="Midtown Arcade")
    db_session.add(location)
    db_session.flush()

    machine = models.Machine(
        id="machine-end-1",
        shared_secret=f"secret-{uuid4().hex}",
        user_id=user.id,
        location_id=location.id,
        game_title="Space Battle",
    )
    db_session.add(machine)
    db_session.commit()

    active_payload = {
        "gameTimeMs": 1000,
        "ballInPlay": 1,
        "scores": [1200, 800],
        "playerUp": 1,
        "playerCount": 2,
        "gameActive": True,
    }
    finished_payload = {
        "gameTimeMs": 1100,
        "ballInPlay": 0,
        "scores": [2200, 1800],
        "playerUp": None,
        "playerCount": 2,
        "gameActive": False,
    }

    response = client.post(
        "/api/v1/machines/game_state",
        json=active_payload,
        headers={"X-Machine-ID": machine.id},
    )
    assert response.status_code == 204

    response = client.post(
        "/api/v1/machines/game_state",
        json=finished_payload,
        headers={"X-Machine-ID": machine.id},
    )
    assert response.status_code == 204

    response = client.get(f"/api/v1/public/locations/{location.id}/scoreboard")
    assert response.status_code == 200
    payload = response.json()

    machine_payload = next(
        item for item in payload["machines"] if item["machine_id"] == machine.id
    )

    # current scores should match the last reported state
    assert machine_payload["scores"] == finished_payload["scores"]

    all_time_scores = machine_payload["high_scores"]["all_time"]
    assert [entry["value"] for entry in all_time_scores] == [2200, 1800]
    assert machine_payload["high_scores"]["daily"] == all_time_scores
    assert machine_payload["high_scores"]["monthly"] == all_time_scores
