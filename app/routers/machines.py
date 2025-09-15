import base64
import os
import secrets
import string
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization

from .. import crud, schemas
from ..database import get_db
from ..utils.signing import sign_json_response
import hmac
import hashlib
from typing import NamedTuple

router = APIRouter(prefix="/machines", tags=["machines"])

logger = logging.getLogger(__name__)


# @router.post("/", response_model=schemas.Machine)
# def register_machine(
#     machine: schemas.MachineCreate,
#     db: Session = Depends(get_db),
#     current_user: crud.models.User = Depends(get_current_user),
# ):
#     existing = crud.get_machine_by_name(db, machine.name)
#     if existing:
#         raise HTTPException(status_code=400, detail="Machine already registered")
#     return crud.create_machine(db, machine, current_user.id)


# @router.get("/me", response_model=list[schemas.Machine])
# def list_my_machines(
#     db: Session = Depends(get_db),
#     current_user: crud.models.User = Depends(get_current_user),
# ):
#     return crud.get_machines_for_user(db, current_user.id)


def get_shared_secret_from_request(request: Request, db: Session) -> bytes:
    """Look up the per-machine shared secret using the X-Machine-ID header."""
    mid_b64 = request.headers.get("X-Machine-ID")
    if not mid_b64:
        raise HTTPException(status_code=400, detail="Missing X-Machine-ID header")
    try:
        base64.b64decode(mid_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Bad X-Machine-ID")

    rec = crud.get_machine(db, mid_b64)
    if rec is None or not rec.shared_secret:
        raise HTTPException(status_code=401, detail=f"Unknown machine {mid_b64}")

    try:
        return base64.b64decode(rec.shared_secret, validate=True)
    except Exception:
        raise HTTPException(status_code=500, detail="Server stored secret decode error")


# @router.post("/checkin")
# def machines_checkin(request: Request, db: Session = Depends(get_db)):
#     """Respond to a machine check-in with a signed payload."""
#     payload = {"messages": [{"type": "claimed"}]}
#     shared_secret = get_shared_secret_from_request(request, db)
#     return sign_json_response(
#         request=request, payload=payload, shared_secret=shared_secret, status_code=200
#     )


# Route to allow machines to request n new challenges
@router.post("/challenges")
def request_challenges(
    request: Request,
    body: schemas.MachineChallengesRequest,
    db: Session = Depends(get_db),
):
    """Generate and return n new challenges for the authenticated machine."""
    n = body.n
    if n < 1 or n > 100:
        raise HTTPException(status_code=400, detail="n must be between 1 and 100")

    shared_secret = get_shared_secret_from_request(request, db)

    mid_b64 = request.headers.get("X-Machine-ID")

    # Remove any existing challenges for this machine
    db.query(crud.models.MachineChallenge).filter_by(machine_id=mid_b64).delete()
    db.commit()

    challenges = []
    for _ in range(n):
        challenge_bytes = os.urandom(16)
        challenge_b64 = base64.b64encode(challenge_bytes).decode("ascii")
        challenges.append(challenge_b64)

        challenge_record = crud.models.MachineChallenge(
            challenge=challenge_b64,
            machine_id=mid_b64,
        )
        db.add(challenge_record)
    db.commit()

    payload = {"challenges": challenges}
    logger.info(f"Generated {n} challenges for machine {mid_b64}: {payload}")
    return sign_json_response(
        request=request, payload=payload, shared_secret=shared_secret, status_code=200
    )


class MachineAuth(NamedTuple):
    id_b64: str
    shared_secret: bytes


async def authenticate_machine(
    request: Request,
    db: Session = Depends(get_db),
) -> MachineAuth:
    """
    Dependency that:
      - Extracts X-Machine-ID
      - Retrieves the shared secret
      - Verifies HMAC (SHA-256) signature over (path + server_challenge + body)
        Signature header format: X-Signature: v1=<base64(hmac_digest)>
    Returns MachineAuth(id_b64, shared_secret) on success.
    """
    mid_b64 = request.headers.get("X-Machine-ID")
    sig_header = request.headers.get("X-Signature")
    challenge_b64 = request.headers.get("X-Server-Challenge")

    if not (mid_b64 and sig_header and challenge_b64):
        raise HTTPException(status_code=401, detail="Missing auth headers")

    if not sig_header.startswith("v1="):
        raise HTTPException(status_code=401, detail="Bad signature version")
    provided_sig_b64 = sig_header[3:]

    try:
        base64.b64decode(mid_b64, validate=True)
        server_challenge_bytes = base64.b64decode(challenge_b64, validate=True)
        provided_sig_bytes = base64.b64decode(provided_sig_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Bad header encoding")

    rec = crud.get_machine(db, mid_b64)
    if rec is None or not rec.shared_secret:
        raise HTTPException(status_code=401, detail="Unknown machine")

    try:
        shared_secret = base64.b64decode(rec.shared_secret, validate=True)
    except Exception:
        raise HTTPException(status_code=500, detail="Server stored secret decode error")

    body = await request.body()
    signed_path = request.url.path.encode("utf-8")
    msg = signed_path + server_challenge_bytes + body
    logging.debug(f"Authenticating machine {mid_b64}: msg={msg}")
    expected_sig_bytes = hmac.new(shared_secret, msg, hashlib.sha256).digest()

    if not hmac.compare_digest(expected_sig_bytes, provided_sig_bytes):
        expected_b64 = base64.b64encode(expected_sig_bytes).decode("ascii")
        logger.warning(
            f"Bad signature for machine {mid_b64}: expected {expected_b64}, got {provided_sig_b64}"
        )
        raise HTTPException(status_code=401, detail="Bad signature")

    return MachineAuth(id_b64=mid_b64, shared_secret=shared_secret)


@router.post("/claim_status", response_model=schemas.MachineClaimStatus)
async def claim_status(
    request: Request,
    auth: MachineAuth = Depends(authenticate_machine),
    db: Session = Depends(get_db),
):
    """Check the status of a machine claim (authenticated)."""
    # Check if machine has an owner
    machine = db.query(crud.models.Machine).filter_by(id=auth.id_hex).first()
    if machine and machine.user_id:
        user = db.query(crud.models.User).filter_by(id=machine.user_id).first()
        payload = {
            "is_claimed": True,
            "claim_url": None,
            "username": user.username if user else None,
        }
        return sign_json_response(
            request=request,
            payload=payload,
            shared_secret=auth.shared_secret,
            status_code=200,
        )

    # If no owner, check for open claim
    claim_model = crud.models.MachineClaim
    claim_record = (
        db.query(claim_model)
        .filter(
            claim_model.machine_id == auth.id_hex,
            claim_model.user_id is None,
            claim_model.claim_code is not None,
        )
        .first()
    )

    if claim_record:
        host = os.environ.get("PUBLIC_HOST_URL", "")
        claim_url = f"{host}/claim?code={claim_record.claim_code}"
        payload = {
            "is_claimed": False,
            "claim_url": claim_url,
            "username": None,
        }
        return sign_json_response(
            request=request,
            payload=payload,
            shared_secret=auth.shared_secret,
            status_code=200,
        )

    # If no owner and no open claim, create a new claim

    alphabet = string.ascii_letters + string.digits
    claim_code = "".join(secrets.choice(alphabet) for _ in range(8))
    new_claim = claim_model(machine_id=auth.id_hex, claim_code=claim_code, user_id=None)
    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)
    host = os.environ.get("PUBLIC_HOST_URL", "")
    claim_url = f"{host}/claim?code={claim_code}"
    payload = {
        "is_claimed": False,
        "claim_url": claim_url,
        "username": None,
    }
    return sign_json_response(
        request=request,
        payload=payload,
        shared_secret=auth.shared_secret,
        status_code=200,
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

    # generate 16 random bytes for machine ID
    machine_id = os.urandom(16)
    machine_id_b64 = base64.b64encode(machine_id).decode("ascii")
    shared_secret_b64 = base64.b64encode(shared_secret).decode("ascii")

    db_machine = crud.models.Machine(
        id=machine_id_b64,
        game_title=handshake.game_title,
        shared_secret=shared_secret_b64,
    )
    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)

    logger.info(
        f"Registered new machine {db_machine.id} for game {db_machine.game_title}"
    )

    payload = {
        "machine_id": machine_id_b64,
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
