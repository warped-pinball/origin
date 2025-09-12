import uuid
import os
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import crud, schemas
from ..database import get_db
from ..auth import get_current_user
from cryptography.hazmat.primitives.asymmetric import x25519

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
def handshake(
    client_public_key_bytes: str,
    game_title: str,
    db: Session = Depends(get_db),
):
    
    client_public_key = x25519.X25519PublicKey.from_public_bytes(client_public_key_bytes)
    
    # generate server public and private key pair
    x25519.X25519PrivateKey.generate()
    server_public_key = server_private_key.public_key()
    shared_secret = server_private_key.exchange(client_public_key)

    # create new machine in db
    machine_uuid = uuid.uuid4()
    machine_uuid_hex = machine_uuid.hex
    machine_id_b64 = b64encode(machine_uuid.bytes).decode("ascii")

    # make a random base64 claim code
    alphabet = string.ascii_letters + string.digits
    claim_code = "".join(secrets.choice(alphabet) for _ in range(8))

    db_claim = models.MachineClaim(
        machine_id=machine_uuid_hex,
        claim_code=claim_code,
        shared_secret=b64encode(shared_secret).decode("ascii"),
        client_game_title=client_game_title,
        claimed=False,
    )
    db.add(db_claim)
    db.commit()

    host = os.environ.get("PUBLIC_HOST_URL", "")
    claim_url = f"{host}/claim?code={claim_code}"

    logger.info("Shared secret (hex) for %s: %s", machine_uuid_hex, shared_secret.hex())

    return schemas.Machine_Handshake(
        machine_id=machine_id_b64,
        claim_url=claim_url,
        server_public_key=b64encode(
            server_public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode("ascii"),
    )

