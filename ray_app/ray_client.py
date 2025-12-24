import asyncio
import os
from datetime import datetime, timedelta
from typing import Iterable

import httpx

from . import udp


class RayApiClient(udp.UDPHandler):
    """Send UDP-derived events to the main app API."""

    def __init__(self, base_url: str | None = None, password: str | None = None):
        default_url = os.getenv("RAY_API_URL") or "http://127.0.0.1:8000"
        self.base_url = (base_url or default_url).rstrip("/")
        self.password = password or os.getenv("RAY_API_PASSWORD")
        if not self.password:
            raise RuntimeError("RAY_API_PASSWORD not configured for RayApiClient")
        self._name_cache: dict[str, tuple[datetime, str | None]] = {}
        self._name_cache_ttl = timedelta(seconds=300)

    async def handle_discovery(
        self, name: str | None, ip: str, peers: Iterable[tuple[str, str]]
    ):
        resolved_name = name or await self._fetch_machine_name(ip)
        payload = {
            "ip": ip,
            "type": "hello" if resolved_name else "full",
            "name": resolved_name,
            "peers": [{"ip": peer_ip, "name": peer_name} for peer_ip, peer_name in peers],
        }
        await self._post("/discovery", payload)

    async def handle_game_state(self, data: dict, ip: str):
        payload = {"ip": ip, "data": dict(data)}
        machine_name = payload["data"].get("machine_name")
        if not (machine_name and machine_name.strip()):
            resolved = await self._fetch_machine_name(ip)
            if resolved:
                payload["data"]["machine_name"] = resolved

        await self._post("/game-state", payload)

    async def _fetch_machine_name(self, ip: str) -> str | None:
        now = datetime.now()
        cached = self._name_cache.get(ip)
        if cached:
            cached_at, cached_name = cached
            if now - cached_at < self._name_cache_ttl:
                return cached_name

        url = f"http://{ip}/api/game/name"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                response.raise_for_status()
                name = None
                try:
                    payload = response.json()
                    name = payload.get("name") or payload.get("machine_name")
                except Exception:
                    # Fall back to treating the body as plain text if JSON parsing fails.
                    name = response.text
                if name and isinstance(name, str):
                    name = name.strip()
                self._name_cache[ip] = (now, name or None)
                return name or None
        except Exception:
            self._name_cache[ip] = (now, None)
            return None

    async def _post(self, path: str, payload: dict) -> None:
        url = f"{self.base_url}/api/v1/ray{path}"
        headers = {"x-ray-password": self.password}
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

    async def ping(self) -> bool:
        try:
            await self._post("/ping", {})
            return True
        except Exception:
            return False

    def ping_blocking(self) -> bool:
        return asyncio.get_event_loop().run_until_complete(self.ping())
