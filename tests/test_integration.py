import pytest
import httpx
import socket
import json
import time
import asyncio

UDP_IP = "127.0.0.1"
UDP_PORT = 5000
API_URL = "http://127.0.0.1:8000"


def send_udp_packet(machine_id, seconds_elapsed, ball, player_up, scores):
    message = {
        "machine_id": machine_id,
        "seconds_elapsed": seconds_elapsed,
        "ball": ball,
        "player_up": player_up,
        "scores": scores,
    }
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(json.dumps(message).encode(), (UDP_IP, UDP_PORT))
    print(f"Sent UDP packet: {message}")


@pytest.mark.asyncio
async def test_udp_to_api_flow():
    # Wait for service to be ready (simple check)
    async with httpx.AsyncClient() as client:
        for i in range(10):
            try:
                resp = await client.get(f"{API_URL}/")
                if resp.status_code == 200:
                    break
            except httpx.ConnectError:
                pass
            time.sleep(1)
        else:
            pytest.fail("API did not become ready in time")

    # Send UDP packet
    machine_id = 999
    send_udp_packet(machine_id, 10, 1, 1, [100, 0, 0, 0])

    # Allow time for processing
    await asyncio.sleep(2)

    # Verify via API
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/games/active")
        assert response.status_code == 200
        games = response.json()

        found = False
        for game in games:
            if game["machine_id"] == machine_id:
                found = True
                break

        assert found, f"Game for machine {machine_id} not found in active games"
