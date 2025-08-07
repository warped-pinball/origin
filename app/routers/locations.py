from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import crud, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/", response_model=list[schemas.Location])
def list_locations(
    db: Session = Depends(get_db),
    current_user: crud.models.User = Depends(get_current_user),
):
    return crud.get_locations_for_user(db, current_user.id)


@router.post("/", response_model=schemas.Location)
def create_location(
    location: schemas.LocationCreate,
    db: Session = Depends(get_db),
    current_user: crud.models.User = Depends(get_current_user),
):
    return crud.create_location(db, current_user.id, location)


@router.put("/{location_id}", response_model=schemas.Location)
def update_location(
    location_id: int,
    location: schemas.LocationCreate,
    db: Session = Depends(get_db),
    current_user: crud.models.User = Depends(get_current_user),
):
    db_location = crud.get_location(db, location_id)
    if not db_location or db_location.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Location not found")
    return crud.update_location(db, db_location, location)


@router.post("/{location_id}/machines", response_model=schemas.Location)
def add_machine(
    location_id: int,
    link: schemas.LocationMachineLink,
    db: Session = Depends(get_db),
    current_user: crud.models.User = Depends(get_current_user),
):
    location = crud.get_location(db, location_id)
    if not location or location.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Location not found")
    machine = crud.get_machine(db, link.machine_id)
    if not machine or machine.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Machine not found")
    crud.set_machine_location(db, machine, location_id)
    db.refresh(location)
    return location
