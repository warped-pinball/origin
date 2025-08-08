from datetime import datetime, timedelta

from ..routers import tournaments as tournaments_router


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def create_user_and_login(
    client, email: str = "user@example.com", password: str = "pass", screen_name: str = "user"
):
    client.post(
        "/api/v1/users/",
        json={"email": email, "password": password, "screen_name": screen_name},
    )
    res = client.post(
        "/api/v1/auth/token", data={"username": email, "password": password}
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    me = client.get("/api/v1/users/me", headers=auth_headers(token))
    user_id = me.json()["id"]
    return token, user_id


def test_create_and_list_tournaments(client):
    tournaments_router._tournaments.clear()
    token, user_id = create_user_and_login(client, "owner@example.com", screen_name="owner")
    headers = auth_headers(token)
    start_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
    response = client.post(
        "/api/v1/tournaments/",
        json={
            "name": "Test Tournament",
            "start_time": start_time,
            "rule_set": "single-elimination",
            "public": True,
            "allow_invites": True,
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Tournament"
    assert data["allow_invites"] is True
    assert data["owner_id"] == user_id

    list_response = client.get("/api/v1/tournaments/", headers=headers)
    assert list_response.status_code == 200
    tournaments = list_response.json()
    assert any(t["id"] == data["id"] for t in tournaments)


def test_register_join_and_manage(client):
    tournaments_router._tournaments.clear()
    owner_token, owner_id = create_user_and_login(
        client, "owner2@example.com", screen_name="owner2"
    )
    headers_owner = auth_headers(owner_token)
    start_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
    response = client.post(
        "/api/v1/tournaments/",
        json={
            "name": "My Tourney",
            "start_time": start_time,
            "rule_set": "single-elimination",
            "public": True,
            "allow_invites": True,
        },
        headers=headers_owner,
    )
    assert response.status_code == 200
    t = response.json()

    participant_token, participant_id = create_user_and_login(
        client, "participant@example.com", screen_name="participant"
    )
    headers_participant = auth_headers(participant_token)

    reg_resp = client.post(
        f"/api/v1/tournaments/{t['id']}/register", headers=headers_participant
    )
    assert reg_resp.status_code == 200

    join_resp = client.post(
        f"/api/v1/tournaments/{t['id']}/join", headers=headers_participant
    )
    assert join_resp.status_code == 200

    manage = client.get(
        f"/api/v1/tournaments/{t['id']}", headers=headers_owner
    )
    assert manage.status_code == 200
    data = manage.json()
    assert data["registered_users"] == [participant_id]
    assert data["joined_users"] == [participant_id]
    assert data["allow_invites"] is True

    update_resp = client.patch(
        f"/api/v1/tournaments/{t['id']}",
        json={"allow_invites": False},
        headers=headers_owner,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["allow_invites"] is False

    bad_update = client.patch(
        f"/api/v1/tournaments/{t['id']}",
        json={"allow_invites": True},
        headers=headers_participant,
    )
    assert bad_update.status_code == 403


def test_list_tournaments_with_filters(client):
    tournaments_router._tournaments.clear()
    token, _ = create_user_and_login(client, "filter@example.com", screen_name="filter")
    headers = auth_headers(token)
    now = datetime.utcnow()

    def create(name: str, delta: int):
        base = now.replace(hour=12, minute=0, second=0, microsecond=0)
        start_time = (base + timedelta(days=delta)).isoformat()
        client.post(
            "/api/v1/tournaments/",
            json={
                "name": name,
                "start_time": start_time,
                "rule_set": "single-elimination",
                "public": True,
                "allow_invites": True,
            },
            headers=headers,
        )

    create("Today", 0)
    create("In5", 5)
    create("In20", 20)
    create("In40", 40)

    resp_today = client.get(
        "/api/v1/tournaments/?filter=today", headers=headers
    )
    assert resp_today.status_code == 200
    assert [t["name"] for t in resp_today.json()] == ["Today"]

    resp_week = client.get(
        "/api/v1/tournaments/?filter=next7", headers=headers
    )
    assert resp_week.status_code == 200
    assert [t["name"] for t in resp_week.json()] == ["Today", "In5"]

    resp_month = client.get(
        "/api/v1/tournaments/?filter=next30", headers=headers
    )
    assert resp_month.status_code == 200
    assert {t["name"] for t in resp_month.json()} == {
        "Today",
        "In5",
        "In20",
    }

    resp_all = client.get(
        "/api/v1/tournaments/?filter=all", headers=headers
    )
    assert resp_all.status_code == 200
    assert {t["name"] for t in resp_all.json()} == {
        "Today",
        "In5",
        "In20",
        "In40",
    }


def test_tournaments_require_authentication(client):
    tournaments_router._tournaments.clear()
    start_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
    response = client.post(
        "/api/v1/tournaments/",
        json={
            "name": "No Auth",
            "start_time": start_time,
            "rule_set": "single-elimination",
            "public": True,
            "allow_invites": True,
        },
    )
    assert response.status_code == 401

    list_response = client.get("/api/v1/tournaments/")
    assert list_response.status_code == 401

    token, _ = create_user_and_login(client, "auther@example.com", screen_name="auther")
    headers = auth_headers(token)
    create_resp = client.post(
        "/api/v1/tournaments/",
        json={
            "name": "Auth Tourney",
            "start_time": start_time,
            "rule_set": "single-elimination",
            "public": True,
            "allow_invites": True,
        },
        headers=headers,
    )
    t = create_resp.json()
    reg_resp = client.post(f"/api/v1/tournaments/{t['id']}/register")
    assert reg_resp.status_code == 401

