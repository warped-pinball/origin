from typing import List, Optional
from sqlalchemy.orm import Session
from .. import models, schemas


def create_machine(db: Session, machine: schemas.MachineCreate, user_id: int) -> models.Machine:
    db_machine = models.Machine(
        name=machine.name,
        secret=machine.secret,
        user_id=user_id,
        location_id=machine.location_id,
    )
    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)
    return db_machine


def get_machine(db: Session, machine_id: int) -> Optional[models.Machine]:
    return db.query(models.Machine).filter(models.Machine.id == machine_id).first()


def get_machine_by_name(db: Session, name: str) -> Optional[models.Machine]:
    return db.query(models.Machine).filter(models.Machine.name == name).first()


def get_machines_for_user(db: Session, user_id: int) -> List[models.Machine]:
    return db.query(models.Machine).filter(models.Machine.user_id == user_id).all()
