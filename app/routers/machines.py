import base64
import os
import secrets
import string
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization

from .. import crud, schemas
from ..auth import get_current_user
from ..database import get_db
from ..utils.signing import sign_json_response

router = APIRouter(prefix="/machines", tags=["machines"])

logger = logging.getLogger(__name__)


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


def get_shared_secret_from_request(request: Request, db: Session) -> bytes:
    """Look up the per-machine shared secret using the X-Machine-ID header."""
    mid_b64 = request.headers.get("X-Machine-ID")
    if not mid_b64:
        raise HTTPException(status_code=400, detail="Missing X-Machine-ID header")
    try:
        machine_id_bytes = base64.b64decode(mid_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Bad X-Machine-ID")

    machine_hex = machine_id_bytes.hex()
    rec = crud.get_machine_secret_by_id_hex(db, machine_hex)
    if rec is None or not rec.shared_secret_b64:
        raise HTTPException(status_code=401, detail="Unknown machine")

    try:
        return base64.b64decode(rec.shared_secret_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=500, detail="Server stored secret decode error")


@router.post("/checkin")
def machines_checkin(request: Request, db: Session = Depends(get_db)):
    """Respond to a machine check-in with a signed payload."""
    payload = {"messages": [{"type": "claimed"}]}
    shared_secret = get_shared_secret_from_request(request, db)
    return sign_json_response(
        request=request, payload=payload, shared_secret=shared_secret, status_code=200
    )


@router.get("/claim_status", response_model=schemas.MachineClaimStatus)
def claim_status(
    request: Request,
    db: Session = Depends(get_db)
):
    """Check the status of a machine claim."""
    shared_secret = get_shared_secret_from_request(request, db)

    #TODO authenticate the request properly

    # Find the claim associated with this machine
    mid_b64 = request.headers.get("X-Machine-ID")
    machine_id_bytes = base64.b64decode(mid_b64, validate=True)
    machine_hex = machine_id_bytes.hex()
    claim = crud.models.MachineClaim
    claim_record = db.query(claim).filter(claim.machine_id == machine_hex).first()
    if not claim_record:
        # Create a new unclaimed record if none exists
        new_claim_record = crud.models.MachineClaim(
            machine_id=machine_hex,
            claim_code=None,
            user_id=None
        )
        db.add(new_claim_record)
        db.commit()
        db.refresh(new_claim_record)
        logger.info(f"Created new machine claim: {new_claim_record}")
        claim_record = new_claim_record

    payload = {}
    if claim_record.user_id:
        user = db.query(crud.models.User).filter(crud.models.User.id == claim_record.user_id).first()
        username = user.username if user else None
        payload={
            "is_claimed": True,
            "claim_url": None,
            "username": username
        }
    elif claim_record.claim_code:
        host = os.environ.get("PUBLIC_HOST_URL", "")
        claim_url = f"{host}/claim?code={claim_record.claim_code}"
        payload={
            "is_claimed": False,
            "claim_url": claim_url,
            "username": None
        }
    else:
        logger.info(f"Machine claim {claim_record.id} is in an unexpected state.")
        logger.debug(f"Claim record details: {claim_record}")
        raise HTTPException(status_code=500, detail="Unexpected machine claim state")

    return sign_json_response(
        request=request,
        payload=payload,
        shared_secret=shared_secret,
        status_code=200
    )

@router.post("/handshake", response_model=schemas.MachineHandshake)
def handshake(
    request: Request,
    handshake: schemas.MachineHandshakeRequest,
    db: Session = Depends(get_db),
):
    client_public_key_bytes = base64.b64decode(handshake.client_public_key_b64)
    client_public_key = x25519.X25519PublicKey.from_public_bytes(
        client_public_key_bytes
    )

    server_private_key = x25519.X25519PrivateKey.generate()
    server_public_key = server_private_key.public_key()
    shared_secret = server_private_key.exchange(client_public_key)

    machine_uuid = uuid.uuid4()
    machine_uuid_hex = machine_uuid.hex
    machine_id_b64 = base64.b64encode(machine_uuid.bytes).decode("ascii")

    alphabet = string.ascii_letters + string.digits
    claim_code = "".join(secrets.choice(alphabet) for _ in range(8))

    shared_secret_b64 = base64.b64encode(shared_secret).decode("ascii")

    db_machine = crud.models.Machine(
        id=machine_uuid_hex,
        game_title=handshake.game_title,
        shared_secret=shared_secret_b64,
    )
    db.add(db_machine)

    db_claim = crud.models.MachineClaim(
        machine_id=machine_uuid_hex,
        claim_code=claim_code,
    )
    db.add(db_claim)
    db.commit()

    host = os.environ.get("PUBLIC_HOST_URL", "")
    claim_url = f"{host}/claim?code={claim_code}"

    payload = {
        "machine_id": machine_id_b64,
        "claim_url": claim_url,
        "server_key": base64.b64encode(
            server_public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode("ascii"),
    }
    return sign_json_response(
        request=request, payload=payload, shared_secret=shared_secret, status_code=200
    )
