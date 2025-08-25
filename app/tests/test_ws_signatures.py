import asyncio
import base64
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)

from app.ws import WSConnection, get_signing_key


class DummyWebSocket:
    def __init__(self):
        self.sent = None

    async def send_text(self, text: str):
        self.sent = text


def test_ws_connection_sends_signed_messages():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    os.environ["RSA_PRIVATE_KEY"] = pem.decode()
    get_signing_key.cache_clear()

    ws = DummyWebSocket()
    conn = WSConnection(ws, "machine1", b"secret")
    asyncio.run(conn.send_json("test", {"hello": "world"}))

    route, payload, signature = ws.sent.split("|", 2)
    assert route == "test"
    message = f"{route}|{payload}".encode("utf-8")
    priv.public_key().verify(
        base64.b64decode(signature),
        message,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

