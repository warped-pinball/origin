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
