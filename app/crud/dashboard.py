"""Data helpers for the public location scoreboard."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from numbers import Number
from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session, aliased, selectinload

from .. import models


def _to_utc_naive(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _state_is_active(
    state: Optional[models.MachineGameState],
) -> bool:
    if state is None:
        return False
    if state.game_active is None:
        return True
    return state.game_active


def _session_states_for_machine(
    db: Session,
    machine_id: str,
    *,
    limit: int = 200,
) -> List[models.MachineGameState]:
    """Return recent states that belong to the latest completed or active game."""

    states_desc: Sequence[models.MachineGameState] = (
        db.query(models.MachineGameState)
        .filter(models.MachineGameState.machine_id == machine_id)
        .order_by(
            models.MachineGameState.created_at.desc(),
            models.MachineGameState.id.desc(),
        )
        .limit(limit)
        .all()
    )

    if not states_desc:
        return []

    session_desc: List[models.MachineGameState] = []
    seen_active = False

    for state in states_desc:
        is_active = _state_is_active(state)

        if session_desc and seen_active and not is_active:
            break

        session_desc.append(state)

        if is_active:
            seen_active = True

    session_states = list(reversed(session_desc))

    if session_states:
        for index, state in enumerate(session_states):
            if _state_is_active(state):
                if index > 0:
                    session_states = session_states[index:]
                break

    return session_states


def _select_display_state(
    states: Sequence[models.MachineGameState],
) -> Optional[models.MachineGameState]:
    if not states:
        return None

    for state in reversed(states):
        if _state_is_active(state):
            return state
        if any(
            isinstance(score, Number) and score > 0
            for score in (state.scores or [])
        ):
            return state

    return states[-1]


def _compute_player_game_times(
    states: Sequence[models.MachineGameState],
    *,
    pause_threshold_seconds: float = 10.0,
) -> List[int]:
    if not states:
        return []

    max_players = max(len(state.scores or []) for state in states)
    if max_players == 0:
        return []

    trackers: List[Dict[str, object]] = [
        {"total": 0.0, "last": None, "ball": None}
        for _ in range(max_players)
    ]
    previous_scores: List[Optional[int]] = [None] * max_players

    for state in states:
        timestamp = _to_utc_naive(state.created_at)
        if timestamp is None:
            continue

        ball = state.ball_in_play
        scores = state.scores or []

        for index in range(max_players):
            raw_score = scores[index] if index < len(scores) else None
            if raw_score is None or not isinstance(raw_score, Number):
                continue

            score = int(raw_score)
            previous = previous_scores[index]
            tracker = trackers[index]

            if tracker.get("ball") != ball and ball is not None:
                tracker["ball"] = ball
                tracker["last"] = None

            if previous is None:
                previous_scores[index] = score
                continue

            delta = score - previous
            if delta > 0 and ball is not None and ball > 0:
                last = tracker["last"]
                if last is not None:
                    elapsed = (timestamp - last).total_seconds()
                    if elapsed < pause_threshold_seconds:
                        tracker["total"] += elapsed
                tracker["last"] = timestamp

            previous_scores[index] = score

    totals: List[int] = []
    for tracker in trackers:
        total_seconds = tracker.get("total", 0.0)
        if not isinstance(total_seconds, (int, float)):
            total_seconds = 0.0
        totals.append(int(round(total_seconds)))

    return totals


def _latest_states_for_location(db: Session, location_id: int) -> Iterable[models.MachineGameState]:
    subquery = (
        db.query(
            models.MachineGameState.machine_id.label("machine_id"),
            func.max(models.MachineGameState.id).label("latest_id"),
        )
        .join(models.Machine, models.Machine.id == models.MachineGameState.machine_id)
        .filter(models.Machine.location_id == location_id)
        .group_by(models.MachineGameState.machine_id)
        .subquery()
    )

    state_alias = aliased(models.MachineGameState)

    return (
        db.query(state_alias)
        .join(
            subquery,
            (state_alias.machine_id == subquery.c.machine_id)
            & (state_alias.id == subquery.c.latest_id),
        )
        .all()
    )


def _top_scores_for_machine(
    db: Session, machine_id: str, *, since: Optional[datetime], limit: int
) -> List[models.Score]:
    query = (
        db.query(models.Score)
        .options(selectinload(models.Score.user))
        .filter(models.Score.machine_id == machine_id)
    )
    if since is not None:
        query = query.filter(models.Score.created_at >= since)

    return (
        query.order_by(models.Score.value.desc(), models.Score.created_at.asc())
        .limit(limit)
        .all()
    )


def build_location_scoreboard(
    db: Session,
    location_id: int,
    *,
    active_within_seconds: int = 180,
    high_score_limit: int = 5,
) -> Optional[Dict[str, object]]:
    location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if location is None:
        return None

    machines = (
        db.query(models.Machine)
        .filter(models.Machine.location_id == location_id)
        .order_by(models.Machine.game_title.asc(), models.Machine.id.asc())
        .all()
    )

    latest_states = list(_latest_states_for_location(db, location_id))
    threshold: Optional[datetime] = None
    if active_within_seconds is not None:
        threshold = datetime.utcnow() - timedelta(seconds=active_within_seconds)

    states_by_machine: Dict[str, models.MachineGameState] = {}
    for state in latest_states:
        created_at = _to_utc_naive(state.created_at)
        if threshold is not None and created_at is not None and created_at < threshold:
            continue
        states_by_machine[state.machine_id] = state

    now = datetime.utcnow()
    windows = {
        "all_time": None,
        "daily": now - timedelta(days=1),
        "weekly": now - timedelta(days=7),
        "monthly": now - timedelta(days=30),
    }

    machine_payloads: List[Dict[str, object]] = []
    for machine in machines:
        latest_state = states_by_machine.get(machine.id)
        is_active = _state_is_active(latest_state)

        session_states: List[models.MachineGameState] = []
        display_state: Optional[models.MachineGameState] = None
        game_time_seconds: List[int] = []

        if latest_state is not None:
            session_states = _session_states_for_machine(db, machine.id)
            if session_states:
                display_state = _select_display_state(session_states)
                game_time_seconds = _compute_player_game_times(session_states)

        scores_for_display: List[int] = []
        if display_state and display_state.scores:
            scores_for_display = [
                int(score) if isinstance(score, Number) and score >= 0 else 0
                for score in display_state.scores
            ]

        ball_in_play = display_state.ball_in_play if display_state else None

        players_total: Optional[int] = None
        if display_state and display_state.players_total is not None:
            players_total = display_state.players_total
        elif latest_state and latest_state.players_total is not None:
            players_total = latest_state.players_total

        player_up: Optional[int] = None
        if is_active and latest_state is not None:
            player_up = latest_state.player_up

        high_scores: Dict[str, List[Dict[str, object]]] = {}
        for label, since in windows.items():
            scores = _top_scores_for_machine(
                db,
                machine.id,
                since=since,
                limit=high_score_limit,
            )
            high_scores[label] = [
                {
                    "value": score.value,
                    "achieved_at": score.created_at,
                    "player_name": (
                        score.user.screen_name
                        if score.user and score.user.screen_name
                        else score.user.name
                        if score.user
                        else None
                    ),
                }
                for score in scores
            ]

        machine_payloads.append(
            {
                "machine_id": machine.id,
                "game_title": machine.game_title,
                "is_active": is_active,
                "updated_at": latest_state.created_at if latest_state else None,
                "scores": scores_for_display,
                "ball_in_play": ball_in_play,
                "player_up": player_up,
                "players_total": players_total,
                "game_time_seconds": game_time_seconds,
                "high_scores": high_scores,
            }
        )

    return {
        "location_id": location.id,
        "location_name": location.name,
        "machines": machine_payloads,
        "generated_at": now,
    }


def get_location_scoreboard_version(
    db: Session, location_id: int
) -> Optional[datetime]:
    """Return the most recent timestamp that should refresh the scoreboard."""

    latest_state: Optional[datetime] = (
        db.query(func.max(models.MachineGameState.created_at))
        .join(
            models.Machine,
            models.MachineGameState.machine_id == models.Machine.id,
        )
        .filter(models.Machine.location_id == location_id)
        .scalar()
    )

    latest_score: Optional[datetime] = (
        db.query(func.max(models.Score.created_at))
        .join(models.Machine, models.Score.machine_id == models.Machine.id)
        .filter(models.Machine.location_id == location_id)
        .scalar()
    )

    candidates = [value for value in (latest_state, latest_score) if value is not None]
    if not candidates:
        return None

    return _to_utc_naive(max(candidates))
