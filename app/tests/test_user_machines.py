from urllib.parse import quote

from .. import models


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def create_user(client, email, password="pass", screen_name=None):
    payload = {"email": email, "password": password}
    if screen_name is None:
        payload["screen_name"] = email.split("@")[0]
    else:
        payload["screen_name"] = screen_name
    response = client.post(
        "/api/v1/users/",
        json=payload,
    )
    assert response.status_code == 200
    return response.json()


def login(client, email, password="pass"):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_list_owned_machines_requires_auth(client):
    response = client.get("/api/v1/machines/me")
    assert response.status_code == 401


def test_list_owned_machines_returns_owned_records(client, db_session):
    user = create_user(client, "machine-owner@example.com")
    other = create_user(client, "machine-other@example.com")
    token = login(client, "machine-owner@example.com")

    location = models.Location(user_id=user["id"], name="Arcade")
    db_session.add(location)
    db_session.commit()

    owned_machine = models.Machine(
        id="owned-machine",
        game_title="Owned Machine",
        shared_secret="secret-owner",
        user_id=user["id"],
        location_id=location.id,
    )
    other_machine = models.Machine(
        id="other-machine",
        game_title="Other Machine",
        shared_secret="secret-other",
        user_id=other["id"],
    )
    db_session.add_all([owned_machine, other_machine])
    db_session.commit()

    response = client.get(
        "/api/v1/machines/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    machine = data[0]
    assert machine["id"] == "owned-machine"
    assert machine["name"] == "Owned Machine"
    assert machine["game_title"] == "Owned Machine"
    assert machine["location_id"] == location.id


def test_list_owned_machines_returns_empty_list_when_none(client):
    create_user(client, "machine-nomachine@example.com")
    token = login(client, "machine-nomachine@example.com")
    response = client.get(
        "/api/v1/machines/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_unregister_machine_clears_owner_and_location(client, db_session):
    owner = create_user(client, "machine-release@example.com")
    location = models.Location(user_id=owner["id"], name="Arcade")
    db_session.add(location)
    db_session.flush()

    machine = models.Machine(
        id="release-machine-id",
        game_title="Release Me",
        shared_secret="release-secret-1",
        user_id=owner["id"],
        location_id=location.id,
        claim_code=None,
    )
    db_session.add(machine)
    db_session.commit()

    token = login(client, "machine-release@example.com")
    response = client.delete(
        f"/api/v1/machines/{quote(machine.id, safe='')}",
        headers=auth_headers(token),
    )

    assert response.status_code == 204
    db_session.refresh(machine)
    assert machine.user_id is None
    assert machine.location_id is None
    assert machine.claim_code is not None


def test_unregister_machine_requires_ownership(client, db_session):
    owner = create_user(client, "machine-owner2@example.com")
    other = create_user(client, "machine-other2@example.com")

    machine = models.Machine(
        id="another-machine-id-unique",
        game_title="Shared",
        shared_secret="shared-secret-other",
        user_id=owner["id"],
        claim_code=None,
    )
    db_session.add(machine)
    db_session.commit()

    token = login(client, "machine-other2@example.com")
    response = client.delete(
        f"/api/v1/machines/{quote(machine.id, safe='')}",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
