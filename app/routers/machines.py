import uuid
import os
import secrets
from fastapi import APIRouter, Depends, HTTPException, Response
from cryptography.hazmat.primitives.asymmetric import x25519

from sqlalchemy.orm import Session
from .. import crud, schemas
from ..database import get_db
from ..auth import get_current_user
from ..utils.signing import sign_json_response

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

# Decorator that signs the reponse of the routes it wraps using the server's private key
def sign_response(func):
    def wrapper(*args, response: Response, **kwargs):
        inner_response = func(*args, **kwargs)

        pem = os.environ.get("RSA_PRIVATE_KEY")
        if not pem:
            raise RuntimeError("RSA_PRIVATE_KEY not configured")
        
        private_key = serialization.load_pem_private_key(pem.encode(), password=None)

        signature = private_key.sign(
            inner_response.content,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        response.headers["X-Signature"] = "signed"  # Placeholder for actual signature
        return inner_response
    return wrapper






# routes_machines.py
import base64
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import get_db
from . import crud  # your DB helpers
from .utils_signing import sign_json_response

router = APIRouter(prefix="/machines", tags=["machines"])

def get_shared_secret_from_request(request: Request, db: Session) -> bytes:
    """
    Example: identify the machine via X-Machine-ID header (base64 of the raw machine_id bytes).
    Look up the per-machine shared secret in your DB (stored base64 in this example).
    Adjust to your schema and handshake storage.
    """
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
        shared_secret = base64.b64decode(rec.shared_secret_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=500, detail="Server stored secret decode error")

    return shared_secret





@router.post("/checkin")
def machines_checkin(request: Request, db: Session = Depends(get_db)):
    """
    Device sends:
      - X-Client-Challenge: base64(32 random bytes, fresh per request)
      - X-Machine-ID: base64(machine_id_bytes) (or whichever identifier you choose)
    We respond with a signed JSON body. The device verifies signature before parsing.
    """
    # Your business logic creates the payload:
    payload = {
        "messages": [
            {"type": "claimed"}
        ]
    }

    shared_secret = get_shared_secret_from_request(request, db)
    return sign_json_response(request=request, payload=payload, shared_secret=shared_secret, status_code=200)


@router.post("/handshake", response_model=schemas.MachineHandshake)
def handshake(
    request: Request,
    client_public_key_b64: str,
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

    payload = {
        "machine_id": machine_id_b64,
        "claim_url": claim_url,
        "claim_code": claim_code,
        "server_key": b64encode(
            server_public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode("ascii"),
    }
    return sign_json_response(request=request, payload=payload, shared_secret=shared_secret, status_code=200)