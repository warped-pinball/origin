from typing import List, Optional

from sqlalchemy.orm import Session

from .. import models, schemas
from ..utils.machines import generate_claim_code


def _is_game_active(active_flag: Optional[bool]) -> bool:
    """Interpret a stored game_active flag with backwards compatibility."""
    if active_flag is None:
        # Older records did not track game_active explicitly; treat them as active
        return True
    return active_flag


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

    became_inactive = False
    if state.game_active is False and previous_state is not None:
        became_inactive = _is_game_active(previous_state.game_active)

    if became_inactive:
        for score_value in state.scores:
            if score_value is None or score_value < 0:
                continue
            db.add(
                models.Score(
                    user_id=None,
                    machine_id=machine.id,
                    game=machine.game_title,
                    value=score_value,
                )
            )

    db.commit()
    db.refresh(record)
    return record
