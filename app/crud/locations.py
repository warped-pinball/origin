from typing import List, Optional
from sqlalchemy.orm import Session
from .. import models, schemas


def create_location(
    db: Session, user_id: int, location: schemas.LocationCreate
) -> models.Location:
    db_location = models.Location(user_id=user_id, **location.model_dump())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


def get_locations_for_user(db: Session, user_id: int) -> List[models.Location]:
    return db.query(models.Location).filter(models.Location.user_id == user_id).all()


def get_location(db: Session, location_id: int) -> Optional[models.Location]:
    return db.query(models.Location).filter(models.Location.id == location_id).first()


def set_machine_location(
    db: Session, machine: models.Machine, location_id: int
) -> models.Machine:
    machine.location_id = location_id
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine


def update_location(
    db: Session, db_location: models.Location, data: schemas.LocationCreate
) -> models.Location:
    for field, value in data.model_dump().items():
        setattr(db_location, field, value)
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location
