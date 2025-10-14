import uuid
from datetime import timedelta

import pytest

from .test_user_machines import auth_headers, create_user, login
from .. import models


@pytest.fixture
def machine(db_session):
    machine = models.Machine(
        id=f"machine-state-{uuid.uuid4()}",
        game_title="Test Game",
        shared_secret=f"shared-secret-{uuid.uuid4()}",
    )
    db_session.add(machine)
    db_session.commit()
    return machine


def test_record_game_state_requires_machine_header(client):
    payload = {"gameTimeMs": 1000, "ballInPlay": 1, "scores": [12345]}
    response = client.post("/api/v1/machines/game_state", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing X-Machine-ID header"


def test_record_game_state_unknown_machine(client):
    payload = {"gameTimeMs": 1000, "ballInPlay": 1, "scores": [1, 2]}
    response = client.post(
        "/api/v1/machines/game_state",
        json=payload,
        headers={"X-Machine-ID": "unknown-machine"},
    )
    assert response.status_code == 404


def test_record_game_state_persists_payload(client, db_session, machine):
    payload = {
        "gameTimeMs": 4567,
        "ballInPlay": 2,
        "scores": [1000, 2000],
        "playerUp": 2,
        "playerCount": 2,
        "gameActive": True,
    }
    response = client.post(
        "/api/v1/machines/game_state",
        json=payload,
        headers={"X-Machine-ID": machine.id},
    )
    assert response.status_code == 204
    states = (
        db_session.query(models.MachineGameState)
        .filter(models.MachineGameState.machine_id == machine.id)
        .all()
    )
    assert len(states) == 1
    state = states[0]
    assert state.time_ms == payload["gameTimeMs"]
    assert state.ball_in_play == payload["ballInPlay"]
    assert state.scores == payload["scores"]
    assert state.player_up == payload["playerUp"]
    assert state.players_total == payload["playerCount"]
    assert state.game_active is True


def test_record_game_state_allows_optional_fields(client, db_session, machine):
    payload = {"gameTimeMs": 999, "ballInPlay": 1, "scores": [321]}
    response = client.post(
        "/api/v1/machines/game_state",
        json=payload,
        headers={"X-Machine-ID": machine.id},
    )
    assert response.status_code == 204
    state = (
        db_session.query(models.MachineGameState)
        .filter(models.MachineGameState.machine_id == machine.id)
        .order_by(models.MachineGameState.id.desc())
        .first()
    )
    assert state.player_up is None
    assert state.players_total is None
    assert state.game_active is None


def test_record_game_state_records_scores_when_game_ends(client, db_session):
    user = models.User(
        email=f"{uuid.uuid4()}@example.com",
        hashed_password="hashed",
        screen_name="Arcader",
    )
    db_session.add(user)
    db_session.flush()

    location = models.Location(user_id=user.id, name="Score Zone")
    db_session.add(location)
    db_session.flush()

    machine = models.Machine(
        id=f"machine-state-{uuid.uuid4()}",
        game_title="Score Game",
        shared_secret=f"shared-secret-{uuid.uuid4()}",
        user_id=user.id,
        location_id=location.id,
    )
    db_session.add(machine)
    db_session.commit()

    active_payload = {
        "gameTimeMs": 1000,
        "ballInPlay": 1,
        "scores": [1_000, 2_000],
        "gameActive": True,
    }
    response = client.post(
        "/api/v1/machines/game_state",
        json=active_payload,
        headers={"X-Machine-ID": machine.id},
    )
    assert response.status_code == 204

    ending_payload = {
        "gameTimeMs": 1500,
        "ballInPlay": 0,
        "scores": [30_000, 12_500],
        "gameActive": False,
    }
    response = client.post(
        "/api/v1/machines/game_state",
        json=ending_payload,
        headers={"X-Machine-ID": machine.id},
    )
    assert response.status_code == 204

    scores = (
        db_session.query(models.Score)
        .filter(models.Score.machine_id == machine.id)
        .order_by(models.Score.value.desc())
        .all()
    )
    assert [score.value for score in scores] == [30_000, 12_500]
    assert all(score.user_id is None for score in scores)
    assert all(score.game == machine.game_title for score in scores)

    # Posting another inactive state should not duplicate scores
    response = client.post(
        "/api/v1/machines/game_state",
        json={**ending_payload, "gameTimeMs": 2000},
        headers={"X-Machine-ID": machine.id},
    )
    assert response.status_code == 204
    updated_scores = (
        db_session.query(models.Score)
        .filter(models.Score.machine_id == machine.id)
        .order_by(models.Score.value.desc())
        .all()
    )
    assert [score.id for score in updated_scores] == [score.id for score in scores]

    response = client.get(
        f"/api/v1/public/locations/{location.id}/scoreboard"
    )
    assert response.status_code == 200
    scoreboard = response.json()
    machine_payload = next(
        m for m in scoreboard["machines"] if m["machine_id"] == machine.id
    )
    assert machine_payload["is_active"] is False
    assert machine_payload["scores"] == ending_payload["scores"]
    assert [
        entry["value"] for entry in machine_payload["high_scores"]["all_time"]
    ] == [30_000, 12_500]


def test_get_latest_machine_state_returns_scores(client, db_session, machine):
    state = models.MachineGameState(
        machine_id=machine.id,
        time_ms=5000,
        ball_in_play=1,
        scores=[1_000, 2_000, 3_000],
        player_up=1,
        players_total=3,
    )
    db_session.add(state)
    db_session.commit()

    user = create_user(client, "machine-state@example.com")
    token = login(client, "machine-state@example.com")

    response = client.get(
        f"/api/v1/machines/{machine.id}/latest_state",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scores"] == [1000, 2000, 3000]
    assert payload["player_up"] == 1
    assert payload["players_total"] == 3


def test_claim_machine_scores_records_entries(client, db_session, machine):
    state = models.MachineGameState(
        machine_id=machine.id,
        time_ms=6000,
        ball_in_play=1,
        scores=[10_000, 20_000],
    )
    db_session.add(state)
    db_session.commit()

    user = create_user(client, "machine-claim@example.com")
    token = login(client, "machine-claim@example.com")

    response = client.post(
        f"/api/v1/machines/{machine.id}/claim_scores",
        headers=auth_headers(token),
        json={"slots": [0, 1]},
    )
    assert response.status_code == 200
    assert response.json()["recorded"] == 2

    scores = (
        db_session.query(models.Score)
        .filter(models.Score.machine_id == machine.id)
        .filter(models.Score.user_id == user["id"])
        .order_by(models.Score.value.asc())
        .all()
    )
    assert [score.value for score in scores] == [10_000, 20_000]

    duplicate_response = client.post(
        f"/api/v1/machines/{machine.id}/claim_scores",
        headers=auth_headers(token),
        json={"slots": [0]},
    )
    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["detail"] == "No new scores recorded"


def test_claim_machine_scores_handles_subsecond_created_at(client, db_session, machine):
    state = models.MachineGameState(
        machine_id=machine.id,
        time_ms=6000,
        ball_in_play=1,
        scores=[42_000, 84_000],
    )
    db_session.add(state)
    db_session.commit()

    user = create_user(client, "machine-subsecond@example.com")
    token = login(client, "machine-subsecond@example.com")

    initial_response = client.post(
        f"/api/v1/machines/{machine.id}/claim_scores",
        headers=auth_headers(token),
        json={"slots": [0, 1]},
    )
    assert initial_response.status_code == 200
    assert initial_response.json()["recorded"] == 2

    latest_state = (
        db_session.query(models.MachineGameState)
        .filter(models.MachineGameState.machine_id == machine.id)
        .order_by(models.MachineGameState.id.desc())
        .first()
    )
    assert latest_state is not None

    scores = (
        db_session.query(models.Score)
        .filter(models.Score.machine_id == machine.id)
        .filter(models.Score.user_id == user["id"])
        .all()
    )
    assert len(scores) == 2

    offset = latest_state.created_at - timedelta(milliseconds=500)
    for score in scores:
        score.created_at = offset
    db_session.commit()

    duplicate_response = client.post(
        f"/api/v1/machines/{machine.id}/claim_scores",
        headers=auth_headers(token),
        json={"slots": [0]},
    )
    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["detail"] == "No new scores recorded"
