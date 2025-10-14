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


def test_record_game_state_records_scores_on_game_end(client, db_session, machine):
    active_payload = {
        "gameTimeMs": 2000,
        "ballInPlay": 1,
        "scores": [5000, 3200],
        "playerUp": 1,
        "playerCount": 2,
        "gameActive": True,
    }
    finished_payload = {
        "gameTimeMs": 2100,
        "ballInPlay": 0,
        "scores": [5800, 4500],
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

    scores = (
        db_session.query(models.Score)
        .filter(models.Score.machine_id == machine.id)
        .order_by(models.Score.value.desc())
        .all()
    )

    assert [score.value for score in scores] == [5800, 4500]
    assert all(score.game == machine.game_title for score in scores)
    assert all(score.user_id is None for score in scores)
