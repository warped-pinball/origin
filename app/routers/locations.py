from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import crud, schemas
from ..utils.urls import build_location_display_url
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/", response_model=list[schemas.Location])
def list_locations(
    db: Session = Depends(get_db),
    current_user: crud.models.User = Depends(get_current_user),
):
    locations = crud.get_locations_for_user(db, current_user.id)
    for location in locations:
        location.display_url = build_location_display_url(location.id)
    return locations


@router.post("/", response_model=schemas.Location)
def create_location(
    location: schemas.LocationCreate,
    db: Session = Depends(get_db),
    current_user: crud.models.User = Depends(get_current_user),
):
    created = crud.create_location(db, current_user.id, location)
    created.display_url = build_location_display_url(created.id)
    return created


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
    updated = crud.update_location(db, db_location, location)
    updated.display_url = build_location_display_url(updated.id)
    return updated


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
    location.display_url = build_location_display_url(location.id)
    return location
