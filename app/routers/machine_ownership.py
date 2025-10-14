from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/machines", tags=["machines"])


@router.get("/me", response_model=list[schemas.OwnedMachine])
def list_owned_machines(
    db: Session = Depends(get_db),
    current_user: crud.models.User = Depends(get_current_user),
):
    machines = crud.get_machines_for_user(db, current_user.id)
    machines.sort(key=lambda machine: (machine.game_title or "").lower())
    return [
        schemas.OwnedMachine(
            id=machine.id,
            name=machine.game_title or machine.id,
            game_title=machine.game_title or machine.id,
            location_id=machine.location_id,
        )
        for machine in machines
    ]


@router.delete("/{machine_id:path}", status_code=204)
def unregister_machine(
    machine_id: str,
    db: Session = Depends(get_db),
    current_user: crud.models.User = Depends(get_current_user),
):
    decoded_machine_id = unquote(machine_id)
    machine = crud.get_machine(db, decoded_machine_id)
    if not machine or machine.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Machine not found")
    crud.release_machine(db, machine)
    return Response(status_code=204)
