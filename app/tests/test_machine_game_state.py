import uuid

import pytest

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


def test_record_game_state_uses_last_active_scores_when_inactive_resets(
    client, db_session, machine
):
    active_payloads = [
        {
            "gameTimeMs": 1000,
            "ballInPlay": 1,
            "scores": [1_000, 2_000],
            "playerUp": 0,
            "gameActive": True,
        },
        {
            "gameTimeMs": 2000,
            "ballInPlay": 1,
            "scores": [5_000, 8_000],
            "playerUp": 1,
            "gameActive": True,
        },
    ]

    for payload in active_payloads:
        response = client.post(
            "/api/v1/machines/game_state",
            json=payload,
            headers={"X-Machine-ID": machine.id},
        )
        assert response.status_code == 204

    ending_payload = {
        "gameTimeMs": 2100,
        "ballInPlay": 0,
        "scores": [0, 0],
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
    assert [score.value for score in scores] == [8_000, 5_000]
    assert all(score.duration_ms is None for score in scores)


def test_record_game_state_calculates_game_durations(client, db_session, machine):
    sequence = [
        {"gameTimeMs": 1000, "ballInPlay": 1, "scores": [0], "playerUp": 0, "gameActive": True},
        {
            "gameTimeMs": 2000,
            "ballInPlay": 1,
            "scores": [100],
            "playerUp": 0,
            "gameActive": True,
        },
        {
            "gameTimeMs": 7000,
            "ballInPlay": 1,
            "scores": [500],
            "playerUp": 0,
            "gameActive": True,
        },
        {
            "gameTimeMs": 22_000,
            "ballInPlay": 1,
            "scores": [1_000],
            "playerUp": 0,
            "gameActive": True,
        },
        {
            "gameTimeMs": 25_000,
            "ballInPlay": 2,
            "scores": [1_000],
            "playerUp": 0,
            "gameActive": True,
        },
        {
            "gameTimeMs": 26_000,
            "ballInPlay": 2,
            "scores": [1_500],
            "playerUp": 0,
            "gameActive": True,
        },
        {
            "gameTimeMs": 30_000,
            "ballInPlay": 0,
            "scores": [0],
            "gameActive": False,
        },
    ]

    for payload in sequence:
        response = client.post(
            "/api/v1/machines/game_state",
            json=payload,
            headers={"X-Machine-ID": machine.id},
        )
        assert response.status_code == 204

    score_record = (
        db_session.query(models.Score)
        .filter(models.Score.machine_id == machine.id)
        .order_by(models.Score.value.desc())
        .first()
    )
    assert score_record is not None
    assert score_record.value == 1_500
    assert score_record.duration_ms == 15_000
