from .. import models


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


def test_add_machine_accepts_string_identifier(client, db_session):
    token = create_user_and_login(client)

    user = db_session.query(models.User).filter_by(email="loc@example.com").first()
    location = models.Location(user_id=user.id, name="Test Arcade")
    db_session.add(location)
    db_session.flush()

    machine = models.Machine(
        id="c16pN+JdX6d0hev8Q2rLjQ==",
        shared_secret="shared-secret-loc",
        user_id=user.id,
        game_title="Pinball",
    )
    db_session.add(machine)
    db_session.commit()

    res = client.post(
        f"/api/v1/locations/{location.id}/machines",
        json={"machine_id": machine.id},
        headers=auth_headers(token),
    )

    assert res.status_code == 200
    db_session.refresh(machine)
    assert machine.location_id == location.id


def test_location_display_url_in_responses(client):
    token = create_user_and_login(client)

    response = client.post(
        "/api/v1/locations/",
        json={"name": "Display Arcade"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_url"].endswith(f"/locations/{data['id']}/display")

    list_response = client.get(
        "/api/v1/locations/",
        headers=auth_headers(token),
    )
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed[0]["display_url"].endswith(f"/locations/{listed[0]['id']}/display")


def test_delete_location_moves_machines_to_unassigned(client, db_session):
    token = create_user_and_login(client)

    user = db_session.query(models.User).filter_by(email="loc@example.com").first()
    location = models.Location(user_id=user.id, name="Delete Arcade")
    db_session.add(location)
    db_session.flush()

    machine = models.Machine(
        id="delete-machine",
        shared_secret="delete-secret",
        user_id=user.id,
        game_title="Delete Test",
        location_id=location.id,
    )
    db_session.add(machine)
    db_session.commit()

    location_id = location.id
    machine_id = machine.id
    db_session.expunge_all()

    response = client.delete(
        f"/api/v1/locations/{location_id}", headers=auth_headers(token)
    )

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.get(models.Location, location_id) is None
    assert db_session.get(models.Machine, machine_id).location_id is None


def test_delete_location_requires_owner(client, db_session):
    token = create_user_and_login(client)
    other_user = models.User(
        email="other@example.com",
        hashed_password="x",
        screen_name="other",
    )
    db_session.add(other_user)
    db_session.flush()

    location = models.Location(user_id=other_user.id, name="Other Arcade")
    db_session.add(location)
    db_session.commit()

    response = client.delete(
        f"/api/v1/locations/{location.id}", headers=auth_headers(token)
    )

    assert response.status_code == 404
