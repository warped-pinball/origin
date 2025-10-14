from typing import Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from .. import models, schemas
from ..utils.machines import generate_claim_code


def _is_game_active(active_flag: Optional[bool]) -> bool:
    """Interpret a stored game_active flag with backwards compatibility."""
    if active_flag is None:
        # Older records did not track game_active explicitly; treat them as active
        return True
    return active_flag


def _fetch_session_states(
    db: Session, machine_id: str, current_state_id: int
) -> List[models.MachineGameState]:
    """Return the game state history for the active session ending at current_state_id."""

    last_inactive_state = (
        db.query(models.MachineGameState.id)
        .filter(models.MachineGameState.machine_id == machine_id)
        .filter(models.MachineGameState.id < current_state_id)
        .filter(models.MachineGameState.game_active.is_(False))
        .order_by(models.MachineGameState.id.desc())
        .first()
    )

    query = db.query(models.MachineGameState).filter(
        models.MachineGameState.machine_id == machine_id,
        models.MachineGameState.id <= current_state_id,
    )
    if last_inactive_state is not None:
        query = query.filter(models.MachineGameState.id > last_inactive_state[0])

    return list(query.order_by(models.MachineGameState.id.asc()))


def _max_scores_from_states(
    states: Sequence[models.MachineGameState],
) -> List[int]:
    """Compute the highest score reached by each player during the session."""

    if not states:
        return []

    player_count = max(len(state.scores or []) for state in states)
    maxima = [0] * player_count

    for state in states:
        for idx in range(player_count):
            try:
                score_value = state.scores[idx]
            except IndexError:
                continue
            if score_value is None or score_value < 0:
                continue
            if score_value > maxima[idx]:
                maxima[idx] = score_value

    return maxima


def _player_game_durations(
    states: Sequence[models.MachineGameState],
    *,
    inactivity_threshold_ms: int = 10_000,
) -> List[Optional[int]]:
    """Estimate the active game time for each player within the session."""

    if not states:
        return []

    player_count = max(len(state.scores or []) for state in states)
    ball_events: List[List[Dict[str, List[int]]]] = [list() for _ in range(player_count)]
    current_ball: List[Optional[int]] = [None] * player_count
    previous_scores: List[Optional[int]] = [None] * player_count

    for state in states:
        scores = state.scores or []
        player_up = state.player_up
        ball_in_play = state.ball_in_play

        for idx in range(player_count):
            score = scores[idx] if idx < len(scores) and scores[idx] is not None else 0
            prev_score = previous_scores[idx]

            if player_up == idx and ball_in_play is not None:
                if current_ball[idx] != ball_in_play:
                    current_ball[idx] = ball_in_play

            score_increased = prev_score is not None and score > prev_score

            if score_increased:
                ball_number = current_ball[idx]
                if ball_number is None:
                    ball_number = ball_in_play or ball_number or 1
                    current_ball[idx] = ball_number

                player_events = ball_events[idx]
                if not player_events or player_events[-1]["ball"] != ball_number:
                    player_events.append({"ball": ball_number, "events": []})
                player_events[-1]["events"].append(state.time_ms)

            previous_scores[idx] = score

    durations: List[Optional[int]] = []
    for idx in range(player_count):
        total = 0
        for ball in ball_events[idx]:
            events = ball["events"]
            if len(events) < 2:
                continue
            start = events[0]
            end = events[-1]
            if end <= start:
                continue
            raw_span = end - start
            inactivity = 0
            for earlier, later in zip(events, events[1:]):
                gap = later - earlier
                if gap > inactivity_threshold_ms:
                    inactivity += gap - inactivity_threshold_ms
            total += max(raw_span - inactivity, 0)
        durations.append(total if total > 0 else None)

    return durations


def create_machine(
    db: Session, machine: schemas.MachineCreate, user_id: int
) -> models.Machine:
    db_machine = models.Machine(
        name=machine.name,
        shared_secret=machine.secret,
        user_id=user_id,
        location_id=machine.location_id,
    )
    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)
    return db_machine


def get_machine(db: Session, machine_id: str) -> Optional[models.Machine]:
    return db.query(models.Machine).filter(models.Machine.id == machine_id).first()


def get_machine_by_name(db: Session, name: str) -> Optional[models.Machine]:
    return db.query(models.Machine).filter(models.Machine.name == name).first()


def get_machines_for_user(db: Session, user_id: int) -> List[models.Machine]:
    return db.query(models.Machine).filter(models.Machine.user_id == user_id).all()


def release_machine(db: Session, machine: models.Machine) -> models.Machine:
    machine.user_id = None
    machine.location_id = None
    machine.claim_code = generate_claim_code()
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine


def record_machine_game_state(
    db: Session, machine: models.Machine, state: schemas.MachineGameStateCreate
) -> models.MachineGameState:
    previous_state = (
        db.query(models.MachineGameState)
        .filter(models.MachineGameState.machine_id == machine.id)
        .order_by(models.MachineGameState.id.desc())
        .first()
    )

    record = models.MachineGameState(
        machine_id=machine.id,
        time_ms=state.game_time_ms,
        ball_in_play=state.ball_in_play,
        scores=state.scores,
        player_up=state.player_up,
        players_total=state.players_total,
        game_active=state.game_active,
    )
    db.add(record)
    db.flush()

    became_inactive = False
    if state.game_active is False and previous_state is not None:
        became_inactive = _is_game_active(previous_state.game_active)

    if became_inactive:
        session_states = _fetch_session_states(db, machine.id, record.id)
        final_scores = _max_scores_from_states(session_states)
        durations = _player_game_durations(session_states)

        for idx, score_value in enumerate(final_scores):
            if score_value is None or score_value < 0:
                continue
            duration_ms = None
            if durations and idx < len(durations):
                duration_ms = durations[idx]
            db.add(
                models.Score(
                    user_id=None,
                    machine_id=machine.id,
                    game=machine.game_title,
                    value=score_value,
                    duration_ms=duration_ms,
                )
            )

    db.commit()
    db.refresh(record)
    return record
