# utils_signing.py
import os
import json
import base64
from typing import Any, Optional

from fastapi import HTTPException, Request, Response
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


# Cache the private key after first load
_RSA_PRIVATE_KEY: Optional[rsa.RSAPrivateKey] = None


def load_rsa_private_key_from_env() -> rsa.RSAPrivateKey:
    """
    Load the server RSA private key from the RSA_PRIVATE_KEY environment variable (PEM).
    The PEM must be unencrypted or provide password handling if you need it.
    This function caches the key for future calls.
    """
    global _RSA_PRIVATE_KEY
    if _RSA_PRIVATE_KEY is not None:
        return _RSA_PRIVATE_KEY

    pem = os.environ.get("RSA_PRIVATE_KEY")
    if not pem:
        raise RuntimeError("RSA_PRIVATE_KEY not configured in environment variables")

    key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise RuntimeError("Loaded key is not an RSA private key")

    _RSA_PRIVATE_KEY = key
    return _RSA_PRIVATE_KEY


def dumps_compact(obj: Any) -> bytes:
    """
    Deterministic JSON serialization:
      - UTF-8
      - sort keys
      - minimal separators
    Produces stable bytes that we sign and return as the HTTP body.
    """
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return s.encode("utf-8")


def sign_json_response(
    request: Request,
    payload: Any,
    shared_secret: bytes,
    status_code: int = 200,
) -> Response:
    """
    Create a signed JSON Response for the device.

    Signature preimage:
        shared_secret + client_challenge + body_bytes

    Signature algorithm:
        RSA PKCS#1 v1.5 with SHA-256 (matches micropython rsa.pkcs1.verify(..., 'SHA-256'))

    Headers set:
        Content-Type: application/json
        X-Signature: base64(signature)

    Raises HTTPException if the client challenge header is missing or invalid.
    """
    if not isinstance(shared_secret, (bytes, bytearray)) or len(shared_secret) == 0:
        raise HTTPException(
            status_code=500, detail="Shared secret unavailable for signing"
        )

    b64_chal = request.headers.get("X-Client-Challenge")
    if not b64_chal:
        raise HTTPException(status_code=400, detail="Missing X-Client-Challenge header")

    try:
        client_challenge = base64.b64decode(b64_chal, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Bad X-Client-Challenge (base64)")

    body_bytes = dumps_compact(payload)

    message = bytes(shared_secret) + client_challenge + body_bytes

    private_key = load_rsa_private_key_from_env()
    signature = private_key.sign(
        data=message,
        padding=padding.PKCS1v15(),
        algorithm=hashes.SHA256(),
    )
    sig_b64 = base64.b64encode(signature).decode("ascii")

    headers = {"X-Signature": sig_b64}
    return Response(
        content=body_bytes,
        media_type="application/json",
        headers=headers,
        status_code=status_code,
    )
