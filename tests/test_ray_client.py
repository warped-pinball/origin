import httpx
import pytest

from ray_app.ray_client import RayApiClient


class _DummyAsyncClient:
    def __init__(self, *_, **__):
        self._request_url = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):  # pragma: no cover - context manager protocol
        return False

    async def get(self, url):
        self._request_url = url
        return httpx.Response(
            200,
            json={"name": "Galaxy Quest"},
            request=httpx.Request("GET", url),
        )


@pytest.mark.asyncio
async def test_handle_discovery_fetches_name(monkeypatch):
    client = RayApiClient(base_url="http://api", password="pw")

    captured = {}

    async def fake_post(path, payload):
        captured.update({"path": path, "payload": payload})

    monkeypatch.setattr(client, "_post", fake_post)
    dummy = _DummyAsyncClient()
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: dummy)

    await client.handle_discovery(None, "5.6.7.8", [])

    assert captured["path"] == "/discovery"
    assert captured["payload"]["name"] == "Galaxy Quest"
    assert captured["payload"]["type"] == "hello"
    assert dummy._request_url == "http://5.6.7.8/api/game/name"


@pytest.mark.asyncio
async def test_handle_game_state_enriches_machine_name(monkeypatch):
    client = RayApiClient(base_url="http://api", password="pw")

    async def fake_name_fetch(ip):
        return "Nebula"

    monkeypatch.setattr(client, "_fetch_machine_name", fake_name_fetch)

    captured = {}

    async def fake_post(path, payload):
        captured.update(payload)

    monkeypatch.setattr(client, "_post", fake_post)

    await client.handle_game_state({"scores": {}}, "10.0.0.9")

    assert captured["data"]["machine_name"] == "Nebula"
    assert captured["ip"] == "10.0.0.9"
