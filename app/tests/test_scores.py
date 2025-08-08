from .. import models


def _create_user_and_token(client, email: str, screen: str):
    client.post(
        "/api/v1/users/",
        json={"email": email, "password": "pass", "screen_name": screen},
    )
    res = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "pass"},
    )
    return res.json()["access_token"]


def test_user_cannot_submit_score_for_another_account(client, db_session):
    token1 = _create_user_and_token(client, "s1@example.com", "s1")
    _create_user_and_token(client, "s2@example.com", "s2")
    user1 = db_session.query(models.User).filter_by(email="s1@example.com").first()
    user2 = db_session.query(models.User).filter_by(email="s2@example.com").first()

    machine = models.Machine(name="ScoreMachine", secret="secret")
    db_session.add(machine)
    db_session.commit()
    db_session.refresh(machine)

    res = client.post(
        "/api/v1/scores/",
        json={
            "game": "pinball",
            "value": 100,
            "machine_id": machine.id,
            "user_id": user2.id,
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["id"] == user1.id
    assert data["user"]["id"] != user2.id

    db_session.expire_all()
    assert db_session.query(models.Score).filter_by(user_id=user2.id).count() == 0
    assert db_session.query(models.Score).filter_by(user_id=user1.id).count() == 1

