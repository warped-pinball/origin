from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import crud, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/machines", tags=["machines"])


@router.post("/", response_model=schemas.Machine)
def register_machine(
    machine: schemas.MachineCreate,
    db: Session = Depends(get_db),
    current_user: crud.models.User = Depends(get_current_user),
):
    existing = crud.get_machine_by_name(db, machine.name)
    if existing:
        raise HTTPException(status_code=400, detail="Machine already registered")
    return crud.create_machine(db, machine, current_user.id)


@router.get("/me", response_model=list[schemas.Machine])
def list_my_machines(
    db: Session = Depends(get_db),
    current_user: crud.models.User = Depends(get_current_user),
):
    return crud.get_machines_for_user(db, current_user.id)


@router.post("/handshake", response_model=schemas.MachineHandshake)
def handshake(payload: dict):
    pass
