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
