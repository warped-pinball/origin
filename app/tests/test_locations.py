import pytest


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def create_user_and_login(client):
    client.post(
        "/api/v1/users/",
        json={"email": "loc@example.com", "password": "pass", "screen_name": "loc"},
    )
    res = client.post(
        "/api/v1/auth/token",
        data={"username": "loc@example.com", "password": "pass"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


def test_location_flow(client):
    token = create_user_and_login(client)
    headers = auth_headers(token)

    loc_res = client.post(
        "/api/v1/locations/",
        json={
            "name": "Arcade",
            "address": "123 St",
            "website": "http://example.com",
            "hours": "Mon-Fri 9-10",
        },
        headers=headers,
    )
    assert loc_res.status_code == 200
    location_id = loc_res.json()["id"]

    mach_res = client.post(
        "/api/v1/machines/",
        json={"name": "M2", "secret": "sec"},
        headers=headers,
    )
    assert mach_res.status_code == 200
    machine_id = mach_res.json()["id"]

    update_res = client.put(
        f"/api/v1/locations/{location_id}",
        json={
            "name": "Arcade Updated",
            "address": "456 Ave",
            "website": "http://example2.com",
            "hours": "24/7",
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Arcade Updated"

    assign_res = client.post(
        f"/api/v1/locations/{location_id}/machines",
        json={"machine_id": machine_id},
        headers=headers,
    )
    assert assign_res.status_code == 200

    machines_list = client.get("/api/v1/machines/me", headers=headers)
    assert machines_list.status_code == 200
    assert machines_list.json()[0]["location_id"] == location_id

    locations_list = client.get("/api/v1/locations/", headers=headers)
    assert locations_list.status_code == 200
    loc_data = locations_list.json()[0]
    assert loc_data["id"] == location_id
    assert loc_data["name"] == "Arcade Updated"
    assert len(loc_data["machines"]) == 1
    assert loc_data["machines"][0]["id"] == machine_id
