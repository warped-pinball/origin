import os
import uuid
import string
import random
from base64 import b64decode, b64encode
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives.asymmetric import x25519, padding
from cryptography.hazmat.primitives import hashes, serialization

from ..database import get_db
from .. import models, schemas

router = APIRouter(tags=["claim"])

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))


@lru_cache()
def get_signing_key():
    pem = os.environ.get("RSA_PRIVATE_KEY")
    if not pem:
        raise RuntimeError("RSA_PRIVATE_KEY not configured")
    return serialization.load_pem_private_key(pem.encode(), password=None)


def generate_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


@router.websocket("/ws/claim")
async def ws_claim(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        payload = await websocket.receive_json()
        client_key_b64 = payload["client_key"]
        client_public_bytes = b64decode(client_key_b64)
        client_public_key = x25519.X25519PublicKey.from_public_bytes(client_public_bytes)
    except Exception:
        await websocket.close()
        return

    server_private_key = x25519.X25519PrivateKey.generate()
    server_public_key = server_private_key.public_key()
    shared_secret = server_private_key.exchange(client_public_key)
    machine_id = str(uuid.uuid4())
    claim_code = generate_code()

    signing_key = get_signing_key()
    signature = signing_key.sign(
        shared_secret, padding.PKCS1v15(), hashes.SHA256()
    )

    db_claim = models.MachineClaim(
        machine_id=machine_id,
        claim_code=claim_code,
        shared_secret=b64encode(shared_secret).decode(),
        claimed=False,
    )
    db.add(db_claim)
    db.commit()

    await websocket.send_json(
        {
            "server_key": b64encode(
                server_public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                )
            ).decode(),
            "claim_code": claim_code,
            "machine_id": machine_id,
            "signature": signature.hex(),
        }
    )
    await websocket.close()


@router.get("/claim", response_class=HTMLResponse)
def claim_page(request: Request, code: str, db: Session = Depends(get_db)):
    claim = (
        db.query(models.MachineClaim)
        .filter(models.MachineClaim.claim_code == code)
        .first()
    )
    if not claim or claim.claimed:
        raise HTTPException(status_code=404, detail="Invalid claim code")
    return templates.TemplateResponse(
        request,
        "claim.html",
        {"code": code, "machine_id": claim.machine_id},
    )


class ClaimRequest(schemas.BaseModel):
    code: str
    user_id: int


@router.post("/api/claim", status_code=204)
def finalize_claim(req: ClaimRequest, db: Session = Depends(get_db)):
    claim = (
        db.query(models.MachineClaim)
        .filter(models.MachineClaim.claim_code == req.code)
        .first()
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Code not found")
    if claim.claimed:
        raise HTTPException(status_code=409, detail="Code already claimed")
    claim.user_id = req.user_id
    claim.claimed = True
    claim.claim_code = None
    db.commit()
    return Response(status_code=204)


@router.get("/api/machines/{machine_id}/status")
def machine_status(machine_id: str, db: Session = Depends(get_db)):
    claim = db.query(models.MachineClaim).filter_by(machine_id=machine_id).first()
    return {"linked": bool(claim and claim.claimed)}
