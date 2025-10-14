"""Data helpers for the public location scoreboard."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, aliased, selectinload

from .. import models


def _to_utc_naive(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _latest_states_for_location(db: Session, location_id: int) -> Iterable[models.MachineGameState]:
    subquery = (
        db.query(
            models.MachineGameState.machine_id.label("machine_id"),
            func.max(models.MachineGameState.created_at).label("latest_created_at"),
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
            & (state_alias.created_at == subquery.c.latest_created_at),
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
        "monthly": now - timedelta(days=30),
    }

    machine_payloads: List[Dict[str, object]] = []
    for machine in machines:
        state = states_by_machine.get(machine.id)
        is_active = state is not None

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
                "updated_at": state.created_at if state else None,
                "scores": state.scores if state else [],
                "ball_in_play": state.ball_in_play if state else None,
                "player_up": state.player_up if state else None,
                "players_total": state.players_total if state else None,
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
