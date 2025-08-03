from datetime import datetime, timedelta

def test_create_and_list_tournaments(client):
    start_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
    response = client.post(
        "/api/v1/tournaments/",
        json={
            "name": "Test Tournament",
            "start_time": start_time,
            "rule_set": "single-elimination",
            "public": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Tournament"
    assert data["id"] == 1

    list_response = client.get("/api/v1/tournaments/")
    assert list_response.status_code == 200
    tournaments = list_response.json()
    assert any(t["id"] == data["id"] for t in tournaments)
