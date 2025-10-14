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


def test_record_game_state_requires_machine_identifier(client):
    payload = {"gameTimeMs": 1000, "ballInPlay": 1, "scores": [12345]}
    response = client.post("/api/v1/machines/game_state", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Machine ID is required"


def test_record_game_state_unknown_machine(client):
    payload = {
        "gameTimeMs": 1000,
        "ballInPlay": 1,
        "scores": [1, 2],
        "machineId": "unknown-machine",
    }
    response = client.post(
        "/api/v1/machines/game_state",
        json=payload,
    )
    assert response.status_code == 404


def test_record_game_state_persists_payload(client, db_session, machine):
    payload = {
        "gameTimeMs": 4567,
        "ballInPlay": 2,
        "scores": [1000, 2000],
        "playerUp": 2,
        "playerCount": 2,
        "machineId": machine.id,
    }
    response = client.post(
        "/api/v1/machines/game_state",
        json=payload,
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


def test_record_game_state_allows_optional_fields(client, db_session, machine):
    payload = {
        "gameTimeMs": 999,
        "ballInPlay": 1,
        "scores": [321],
        "machineId": machine.id,
    }
    response = client.post(
        "/api/v1/machines/game_state",
        json=payload,
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


def test_record_game_state_accepts_header_identifier(client, db_session, machine):
    payload = {"gameTimeMs": 321, "ballInPlay": 1, "scores": [111]}
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
    assert state.time_ms == payload["gameTimeMs"]


def test_record_game_state_accepts_alternate_field_names(client, db_session, machine):
    payload = {
        "game_time_ms": 654,
        "ball_in_play": 3,
        "scores": [0, 0, 0],
        "player_up": 1,
        "players_total": 3,
        "machine_id_b64": machine.id,
    }
    response = client.post("/api/v1/machines/game_state", json=payload)
    assert response.status_code == 204
    state = (
        db_session.query(models.MachineGameState)
        .filter(models.MachineGameState.machine_id == machine.id)
        .order_by(models.MachineGameState.id.desc())
        .first()
    )
    assert state.time_ms == payload["game_time_ms"]
    assert state.ball_in_play == payload["ball_in_play"]
    assert state.player_up == payload["player_up"]
    assert state.players_total == payload["players_total"]
