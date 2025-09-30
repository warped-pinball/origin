from .. import models


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
