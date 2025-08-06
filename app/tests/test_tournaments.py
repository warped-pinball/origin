from datetime import datetime, timedelta

from ..routers import tournaments as tournaments_router

def test_create_and_list_tournaments(client):
    tournaments_router._tournaments.clear()
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
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Tournament"
    assert data["allow_invites"] is True

    list_response = client.get("/api/v1/tournaments/")
    assert list_response.status_code == 200
    tournaments = list_response.json()
    assert any(t["id"] == data["id"] for t in tournaments)


def test_register_join_and_manage(client):
    tournaments_router._tournaments.clear()
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
    )
    assert response.status_code == 200
    t = response.json()

    reg_resp = client.post(f"/api/v1/tournaments/{t['id']}/register", json={"user_id": 2})
    assert reg_resp.status_code == 200

    join_resp = client.post(f"/api/v1/tournaments/{t['id']}/join", json={"user_id": 3})
    assert join_resp.status_code == 200

    manage = client.get(f"/api/v1/tournaments/{t['id']}")
    assert manage.status_code == 200
    data = manage.json()
    assert data["registered_users"] == [2]
    assert data["joined_users"] == [3]
    assert data["allow_invites"] is True

    update_resp = client.patch(
        f"/api/v1/tournaments/{t['id']}", json={"allow_invites": False}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["allow_invites"] is False


def test_list_tournaments_with_filters(client):
    tournaments_router._tournaments.clear()
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
        )

    create("Today", 0)
    create("In5", 5)
    create("In20", 20)
    create("In40", 40)

    resp_today = client.get("/api/v1/tournaments/?filter=today")
    assert resp_today.status_code == 200
    assert [t["name"] for t in resp_today.json()] == ["Today"]

    resp_week = client.get("/api/v1/tournaments/?filter=next7")
    assert resp_week.status_code == 200
    assert [t["name"] for t in resp_week.json()] == ["In5"]

    resp_month = client.get("/api/v1/tournaments/?filter=next30")
    assert resp_month.status_code == 200
    assert {t["name"] for t in resp_month.json()} == {"In5", "In20"}

    resp_all = client.get("/api/v1/tournaments/?filter=all")
    assert resp_all.status_code == 200
    assert {t["name"] for t in resp_all.json()} == {"Today", "In5", "In20", "In40"}
