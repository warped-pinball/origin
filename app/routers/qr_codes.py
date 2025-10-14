from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/qr-codes", tags=["qr_codes"])


def _serialize_qr(
    qr: models.QRCode,
    machines: Dict[str, models.Machine],
) -> schemas.QRCodeDetail:
    machine = machines.get(qr.machine_id) if qr.machine_id else None
    label: Optional[str] = None
    if machine is not None:
        label = machine.game_title or machine.id
    return schemas.QRCodeDetail(
        id=qr.id,
        url=qr.url,
        code=qr.nfc_link,
        created_at=qr.created_at,
        machine_id=qr.machine_id,
        machine_label=label,
    )


@router.get("/", response_model=list[schemas.QRCodeDetail])
def list_owned_qr_codes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    qrs = (
        db.query(models.QRCode)
        .filter(models.QRCode.user_id == current_user.id)
        .order_by(models.QRCode.created_at.asc())
        .all()
    )

    machine_ids = {qr.machine_id for qr in qrs if qr.machine_id}
    machine_lookup: Dict[str, models.Machine] = {}
    if machine_ids:
        machines = (
            db.query(models.Machine)
            .filter(models.Machine.id.in_(machine_ids))
            .all()
        )
        machine_lookup = {machine.id: machine for machine in machines}

    return [_serialize_qr(qr, machine_lookup) for qr in qrs]


@router.patch("/{qr_id}", response_model=schemas.QRCodeDetail)
def update_qr_assignment(
    qr_id: int,
    payload: schemas.QRCodeAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    qr = (
        db.query(models.QRCode)
        .filter(models.QRCode.id == qr_id)
        .first()
    )
    if qr is None or qr.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="QR code not found")

    target_machine: Optional[models.Machine] = None
    if payload.machine_id:
        target_machine = (
            db.query(models.Machine)
            .filter(
                models.Machine.id == payload.machine_id,
                models.Machine.user_id == current_user.id,
            )
            .first()
        )
        if target_machine is None:
            raise HTTPException(status_code=400, detail="Invalid machine")
        qr.machine_id = target_machine.id
    else:
        qr.machine_id = None

    db.add(qr)
    db.commit()
    db.refresh(qr)

    machine_lookup: Dict[str, models.Machine] = {}
    if target_machine:
        machine_lookup[target_machine.id] = target_machine
    elif qr.machine_id:
        machine = (
            db.query(models.Machine)
            .filter(models.Machine.id == qr.machine_id)
            .first()
        )
        if machine:
            machine_lookup[machine.id] = machine

    return _serialize_qr(qr, machine_lookup)
