import json
from base64 import b64decode, b64encode
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519

from app import models, mqtt_app


class DummyMQTTClient:
    def publish(self, topic, message):  # pragma: no cover - stub
        pass


def test_handle_handshake_creates_machine(db_session, monkeypatch):
    """Ensure handshake creates a machine with string ID and shared secret."""
    monkeypatch.setattr(mqtt_app, "send_message", lambda *args, **kwargs: None)

    client_private = x25519.X25519PrivateKey.generate()
    client_public = client_private.public_key()
    message_data = {
        "client_key": b64encode(
            client_public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode("ascii"),
        "game_title": "TestGame",
    }
    mqtt_app.handle_handshake(db_session, DummyMQTTClient(), json.dumps(message_data))

    machine = db_session.query(models.Machine).first()
    assert machine is not None
    assert isinstance(machine.id, str) and len(machine.id) == 32
    secret_bytes = b64decode(machine.shared_secret)
    assert len(secret_bytes) == 32
    assert machine.game_title == "TestGame"
