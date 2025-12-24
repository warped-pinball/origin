import asyncio
import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

# Use a lightweight, file-based SQLite database when the test suite runs so the
# application can initialize without an external PostgreSQL instance.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin")

# Ensure the repository root is on the import path so ``api_app`` can be resolved
# when running tests without installing the package.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from api_app.routers import admin as admin_router
from api_app.main import app
from api_app import database, models
from api_app.database import Base, engine

# Use a separate database for testing or just the same one for simplicity in this context
# For robust testing, we should use a separate DB. 
# Here we will assume the environment is set up correctly (e.g. by docker-compose or CI)

@pytest_asyncio.fixture(scope="function")
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    await database.init_db()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_database_backend_is_sqlite():
    assert engine.url.get_backend_name() == "sqlite"

@pytest.mark.asyncio
async def test_root_redirects_to_registration(async_client):
    response = await async_client.get("/")
    assert response.status_code == 307
    assert response.headers["location"] == "/register"


@pytest.mark.asyncio
async def test_non_api_routes_redirect_to_home(async_client):
    response = await async_client.get("/does-not-exist")
    assert response.status_code == 307
    assert response.headers["location"] == "/register"


@pytest.mark.asyncio
async def test_api_routes_are_not_redirected(async_client):
    response = await async_client.get("/api/v1/players/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_registration_page_served(async_client):
    response = await async_client.get("/register")
    assert response.status_code == 200
    assert "Registration" in response.text
    assert "Game Ready" not in response.text
    assert "registration-form" in response.text
    assert "Warped Pinball" in response.text
    assert "Registration" in response.text
    assert "Players" in response.text
    assert "Brand guide" in response.text
    assert "Component guide" in response.text
    assert "API docs" in response.text
    assert "href=\"/admin\"" in response.text
    assert "Initials, screen name, and email are required" in response.text
    assert "Recent registrations" not in response.text
    assert "Player intake" not in response.text


@pytest.mark.asyncio
async def test_player_profile_page_served(async_client):
    player_resp = await async_client.post(
        "/api/v1/players/",
        json={"initials": "CUP", "screen_name": "Cupcake", "email": "cup@example.com"},
    )
    player_id = player_resp.json()["id"]

    response = await async_client.get(f"/players/{player_id}")
    assert response.status_code == 200
    assert "Player profile" in response.text
    assert "player-form" in response.text
    assert "Warped Pinball" in response.text
    assert "Players" in response.text
    assert "Stats" in response.text
    assert "Edit player" in response.text
    assert "Contact info stays private." in response.text


@pytest.mark.asyncio
async def test_player_roster_page_served(async_client):
    response = await async_client.get("/players")
    assert response.status_code == 200
    assert "Players" in response.text
    assert "roster-list" in response.text
    assert "Brand guide" in response.text
    assert "Component guide" in response.text
    assert "href=\"/admin\"" in response.text


@pytest.mark.asyncio
async def test_registration_assets_served(async_client):
    response = await async_client.get("/static/js/register.js")
    assert response.status_code == 200
    assert "handleSubmit" in response.text


@pytest.mark.asyncio
async def test_brand_guide_page_served(async_client):
    response = await async_client.get("/brand-guide")
    assert response.status_code == 200
    assert "Brand guide" in response.text
    assert "Core palette" in response.text
    assert "guide-grid" in response.text
    assert '<ul class="swatches">' in response.text
    assert '<li class="swatch">' in response.text
    assert "Warped Pinball" in response.text
    assert "logo.svg" in response.text
    assert "Spiral glow" in response.text
    assert "Spiral deep sky" in response.text
    assert "#92c7d7" in response.text
    assert "#caf5fe" in response.text


@pytest.mark.asyncio
async def test_brand_guide_assets_served(async_client):
    response = await async_client.get("/static/css/brand-guide.css")
    assert response.status_code == 200
    assert "guide-grid" in response.text
    assert "flex-direction: column;" in response.text
    assert "grid-template-rows: auto auto;" in response.text
    assert "grid-column: 1 / -1;" in response.text


@pytest.mark.asyncio
async def test_tokens_expose_layout_variables(async_client):
    response = await async_client.get("/static/css/tokens.css")
    assert response.status_code == 200
    assert "--page-background" in response.text
    assert "--space-800" in response.text


@pytest.mark.asyncio
async def test_component_guide_page_served(async_client):
    response = await async_client.get("/component-guide")
    assert response.status_code == 200
    assert "Component guide" in response.text
    assert "Component library" in response.text
    assert "c-nav__link" in response.text
    assert "c-accordion__item" in response.text
    assert "c-card c-card--window" in response.text


@pytest.mark.asyncio
async def test_component_styles_served(async_client):
    response = await async_client.get("/static/css/components.css")
    assert response.status_code == 200
    assert "c-card" in response.text
    assert "c-list__header" in response.text
    assert "c-accordion__item" in response.text


@pytest.mark.asyncio
async def test_header_logo_styles_maximized(async_client):
    response = await async_client.get("/static/css/register.css")
    assert response.status_code == 200
    assert "padding: 4px 22px;" in response.text
    assert "height: 80px" in response.text


@pytest.mark.asyncio
async def test_big_screen_page_served(async_client):
    response = await async_client.get("/big-screen")
    assert response.status_code == 200
    assert "screen-nav" in response.text
    assert "status-banner" in response.text
    assert "leaderboard" in response.text


@pytest.mark.asyncio
async def test_big_screen_styles_remove_pills(async_client):
    response = await async_client.get("/static/css/big-screen.css")
    assert response.status_code == 200
    assert "champion__banner" in response.text
    assert "grid-template-columns: minmax(64px, 0.7fr) minmax(0, 2fr) minmax(150px, 1fr);" in response.text
    assert "game-board--active" in response.text
    assert "score__date" in response.text
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in response.text
    assert "grid-template-rows: repeat(2, minmax(0, 1fr));" in response.text
    assert "max-width: none;" in response.text


@pytest.mark.asyncio
async def test_player_search_includes_contact_fields(async_client):
    await async_client.post(
        "/api/v1/players/",
        json={
            "initials": "AAA",
            "screen_name": "Alpha",
            "email": "alpha@example.com",
            "phone_number": "111-222-3333",
        },
    )
    await async_client.post(
        "/api/v1/players/",
        json={
            "initials": "BBB",
            "screen_name": "Beta",
            "email": "beta@example.com",
            "phone_number": "999-555-1234",
        },
    )

    email_search = await async_client.get("/api/v1/players/?search=alpha@")
    phone_search = await async_client.get("/api/v1/players/?search=999-555")

    assert any(player["initials"] == "AAA" for player in email_search.json())
    assert any(player["initials"] == "BBB" for player in phone_search.json())


@pytest.mark.asyncio
async def test_leaderboard_summary_includes_time_windows(async_client):
    response = await async_client.get("/api/v1/leaderboard/summary")
    assert response.status_code == 200
    payload = response.json()

    assert payload["games"]
    assert payload["leaderboards"]
    assert payload["total_boards"] == len(payload["leaderboards"])

    first_game = payload["games"][0]
    window_slugs = {window["slug"] for window in first_game["windows"]}
    expected_suffixes = {"all-time", "year", "month", "week", "24h"}
    for suffix in expected_suffixes:
        assert any(slug.endswith(suffix) for slug in window_slugs)

    champion = first_game.get("champion")
    if champion:
        all_time_window = next(window for window in first_game["windows"] if window["slug"].endswith("all-time"))
        assert all_time_window["leaderboard"][0] == champion


@pytest.mark.asyncio
async def test_leaderboard_summary_hides_empty_windows(async_client):
    outdated = datetime.now(timezone.utc) - timedelta(days=800)
    async with database.AsyncSessionLocal() as session:
        await session.execute(update(models.GameState).values(timestamp=outdated))
        await session.execute(update(models.Game).values(start_time=outdated, end_time=outdated + timedelta(minutes=45)))
        await session.commit()

    response = await async_client.get("/api/v1/leaderboard/summary")
    payload = response.json()
    windows = payload["games"][0]["windows"]

    assert any(window["slug"].endswith("24h") for window in windows)
    assert any(window["slug"].endswith("week") for window in windows)
    assert any(window["slug"].endswith("month") for window in windows)
    assert any(window["slug"].endswith("year") for window in windows)


@pytest.mark.asyncio
async def test_discovered_games_expose_machine_uid(async_client):
    async with database.AsyncSessionLocal() as session:
        machine = models.Machine(name="Beacon", ip_address="10.1.1.1", uid="uid-discovered")
        session.add(machine)
        session.add(models.Game(machine=machine, is_active=True))
        await session.commit()

    response = await async_client.get("/api/v1/games/discovered")
    assert response.status_code == 200

    payload = response.json()
    assert payload
    assert any(game["machine_uid"] == "uid-discovered" for game in payload)


@pytest.mark.asyncio
async def test_leaderboard_summary_supports_pagination(async_client):
    first_page = await async_client.get("/api/v1/leaderboard/summary", params={"limit": 2})
    assert first_page.status_code == 200
    payload = first_page.json()

    assert len(payload["leaderboards"]) <= 2
    total_boards = payload["total_boards"]
    assert total_boards >= len(payload["leaderboards"])

    second_page = await async_client.get(
        "/api/v1/leaderboard/summary", params={"limit": 2, "offset": 5}
    )
    assert second_page.status_code == 200
    second_payload = second_page.json()

    assert second_payload["total_boards"] == total_boards
    assert len(second_payload["leaderboards"]) <= 2
    assert second_payload["leaderboards"]


@pytest.mark.asyncio
async def test_leaderboard_summary_is_scoped_per_game(async_client):
    response = await async_client.get("/api/v1/leaderboard/summary")
    payload = response.json()

    week_windows = []
    for game in payload["games"]:
        matching = [window for window in game["windows"] if window["slug"].endswith("week")]
        assert matching
        week_windows.extend(matching)

    titles = {board["title"] for board in week_windows}
    assert any("Nebula Orbit" in title for title in titles)
    assert any("Gravity Well" in title for title in titles)

    for board in week_windows:
        if not board["leaderboard"]:
            continue
        machine_names = {entry.get("machine_name") for entry in board["leaderboard"]}
        assert len(machine_names) == 1


@pytest.mark.asyncio
async def test_roster_assets_served(async_client):
    response = await async_client.get("/static/js/players.js")
    assert response.status_code == 200
    assert "loadPlayers" in response.text


@pytest.mark.asyncio
async def test_player_creation_requires_screen_name_and_email(async_client):
    response = await async_client.post("/api/v1/players/", json={"initials": "REQ"})
    assert response.status_code == 422
    response = await async_client.post(
        "/api/v1/players/", json={"initials": "REQ", "screen_name": "Req"}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_machine(async_client):
    response = await async_client.post(
        "/api/v1/machines/",
        json={"name": "Test Machine", "ip_address": "127.0.0.1", "uid": "test-machine"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Machine"
    assert "id" in data

@pytest.mark.asyncio
async def test_create_game(async_client):
    # First create a machine
    m_resp = await async_client.post(
        "/api/v1/machines/",
        json={"name": "Game Machine", "ip_address": "127.0.0.1", "uid": "game-machine"},
    )
    machine_id = m_resp.json()["id"]

    response = await async_client.post("/api/v1/games/", json={"machine_id": machine_id})
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == machine_id
    assert data["is_active"] == True


@pytest.mark.asyncio
async def test_discovered_games_endpoint(async_client):
    response = await async_client.get("/api/v1/games/discovered")
    assert response.status_code == 200
    games = response.json()
    assert games
    assert all("machine_name" in game for game in games)
    assert all("has_password" in game for game in games)


@pytest.mark.asyncio
async def test_admin_can_set_game_password(async_client):
    games_resp = await async_client.get("/api/v1/games/discovered")
    game_id = games_resp.json()[0]["id"]

    credentials = base64.b64encode(b"admin:test-admin").decode()
    update_resp = await async_client.put(
        f"/api/v1/admin/games/{game_id}/password",
        headers={"Authorization": f"Basic {credentials}"},
        json={"password": "hunter2"},
    )

    assert update_resp.status_code == 200
    status = update_resp.json()
    assert status["id"] == game_id
    assert status["has_password"] is True

    refreshed = await async_client.get("/api/v1/games/discovered")
    assert any(game["id"] == game_id and game["has_password"] for game in refreshed.json())


@pytest.mark.asyncio
async def test_udp_discovery_creates_machine_and_game(async_client, monkeypatch):
    from api_app import udp

    async def fake_fetch_uid(ip):
        return f"uid-{ip}"

    monkeypatch.setattr(udp, "_fetch_machine_uid", fake_fetch_uid)

    protocol = udp.UDPProtocol()
    hello = udp.DiscoveryMessage.hello(b"Test Board")
    await protocol.process_message(hello.encode(), ("192.168.1.50", udp.DISCOVERY_PORT))

    machines_resp = await async_client.get("/api/v1/machines/")
    machines = machines_resp.json()
    assert any(machine["ip_address"] == "192.168.1.50" for machine in machines)

    games_resp = await async_client.get("/api/v1/games/discovered")
    games = games_resp.json()
    assert any(game["machine_ip"] == "192.168.1.50" for game in games)


@pytest.mark.asyncio
async def test_udp_discovery_updates_existing_machine_by_uid(async_client, monkeypatch):
    from api_app import udp

    uid_map = {"192.168.1.50": "machine-uid"}

    async def fake_fetch_uid(ip):
        return uid_map.get(ip, "machine-uid")

    monkeypatch.setattr(udp, "_fetch_machine_uid", fake_fetch_uid)

    protocol = udp.UDPProtocol()
    hello = udp.DiscoveryMessage.hello(b"Test Board")

    await protocol.process_message(hello.encode(), ("192.168.1.50", udp.DISCOVERY_PORT))

    # Same machine reports in with a new IP
    await protocol.process_message(hello.encode(), ("192.168.1.51", udp.DISCOVERY_PORT))

    machines_resp = await async_client.get("/api/v1/machines/")
    machines = machines_resp.json()

    matching = [machine for machine in machines if machine["uid"] == "machine-uid"]
    assert len(matching) == 1
    assert matching[0]["ip_address"] == "192.168.1.51"


@pytest.mark.asyncio
async def test_udp_game_state_creates_machine_and_state(async_client, monkeypatch):
    from api_app import udp

    async def fake_fetch_uid(ip):
        return f"uid-{ip}"

    monkeypatch.setattr(udp, "_fetch_machine_uid", fake_fetch_uid)

    payload = {
        "machine_id": "abc123",
        "gameTimeMs": 5000,
        "scores": [1000, 2000],
        "ball_in_play": 2,
        "game_active": True,
    }

    protocol = udp.UDPProtocol()
    await protocol.process_message(
        json.dumps(payload).encode(), ("192.168.1.60", udp.GAME_STATE_PORT)
    )

    machines_resp = await async_client.get("/api/v1/machines/")
    machines = machines_resp.json()
    assert any(machine["ip_address"] == "192.168.1.60" for machine in machines)

    async with database.AsyncSessionLocal() as session:
        result = await session.execute(
            select(models.GameState)
            .join(models.Game)
            .join(models.Machine)
            .where(models.Machine.ip_address == "192.168.1.60")
            .order_by(models.GameState.id.desc())
        )
        states = result.scalars().all()
        assert states
        assert states[0].seconds_elapsed == 5
        assert states[0].ball == 2

        result_machine = await session.execute(
            select(models.Machine).where(models.Machine.ip_address == "192.168.1.60")
        )
        machine = result_machine.scalars().first()
        assert machine.uid == "abc123"


@pytest.mark.asyncio
async def test_udp_game_state_links_existing_machine(async_client, monkeypatch):
    from api_app import udp

    async def fake_fetch_uid(ip):
        return f"uid-{ip}"

    monkeypatch.setattr(udp, "_fetch_machine_uid", fake_fetch_uid)

    async with database.AsyncSessionLocal() as session:
        machine = models.Machine(
            name="Existing", uid="shared-uid", ip_address="192.168.1.55", last_seen=datetime.now(timezone.utc)
        )
        session.add(machine)
        await session.commit()

    payload = {
        "machine_id": "shared-uid",
        "gameTimeMs": 9000,
        "scores": [1234, 5678, 0, 0],
        "ball_in_play": 1,
        "game_active": True,
    }

    protocol = udp.UDPProtocol()
    await protocol.process_message(
        json.dumps(payload).encode(), ("192.168.1.70", udp.GAME_STATE_PORT)
    )

    async with database.AsyncSessionLocal() as session:
        result = await session.execute(
            select(models.GameState)
            .join(models.Game)
            .join(models.Machine)
            .where(models.Machine.uid == "shared-uid")
        )
        state = result.scalars().first()
        assert state is not None
        assert state.seconds_elapsed == 9

        machine_row = await session.execute(
            select(models.Machine).where(models.Machine.uid == "shared-uid")
        )
        machine = machine_row.scalars().first()
        assert machine.ip_address == "192.168.1.70"


@pytest.mark.asyncio
async def test_get_and_update_player(async_client):
    create_resp = await async_client.post(
        "/api/v1/players/",
        json={"initials": "ACE", "screen_name": "Ace", "email": "ace@example.com"},
    )
    assert create_resp.status_code == 200
    player_id = create_resp.json()["id"]

    detail_resp = await async_client.get(f"/api/v1/players/{player_id}")
    assert detail_resp.status_code == 200
    payload = detail_resp.json()
    assert payload["initials"] == "ACE"
    assert "email" not in payload
    assert "phone_number" not in payload
    assert payload.get("stats", {}).get("total_games") == 0

    update_resp = await async_client.put(
        f"/api/v1/players/{player_id}", json={"initials": "ACE", "phone_number": "123-456-7890"}
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert "phone_number" not in data
    assert "email" not in data
    assert data["initials"] == "ACE"


@pytest.mark.asyncio
async def test_update_requires_contact(async_client):
    create_resp = await async_client.post(
        "/api/v1/players/",
        json={"initials": "NOC", "screen_name": "NoContact", "email": "noc@example.com"},
    )
    player_id = create_resp.json()["id"]

    update_resp = await async_client.put(
        f"/api/v1/players/{player_id}",
        json={"screen_name": "StillNoContact"},
    )

    assert update_resp.status_code == 400
    assert "Provide a phone number or email" in update_resp.json()["detail"]


@pytest.mark.asyncio
async def test_public_players_do_not_include_email(async_client):
    await async_client.post(
        "/api/v1/players/",
        json={"initials": "PUB", "screen_name": "Public", "email": "public@example.com"},
    )

    response = await async_client.get("/api/v1/players/")
    payload = response.json()
    assert payload
    assert "email" not in payload[0]
    assert "phone_number" not in payload[0]


@pytest.mark.asyncio
async def test_player_detail_includes_stats(async_client):
    roster_resp = await async_client.get("/api/v1/players/")
    roster = roster_resp.json()
    assert roster

    player_id = roster[0]["id"]
    detail_resp = await async_client.get(f"/api/v1/players/{player_id}")
    assert detail_resp.status_code == 200

    stats = detail_resp.json().get("stats")
    assert stats is not None
    assert "total_games" in stats
    assert "best_score" in stats
    assert "last_game" in stats


@pytest.mark.asyncio
async def test_player_search_by_screen_and_names(async_client):
    await async_client.post(
        "/api/v1/players/",
        json={"initials": "SR1", "screen_name": "Searcher", "first_name": "Sam", "last_name": "Riley", "email": "s1@example.com"},
    )
    await async_client.post(
        "/api/v1/players/",
        json={"initials": "SR2", "screen_name": "Another", "first_name": "Alex", "last_name": "Riley", "email": "s2@example.com"},
    )

    screen_resp = await async_client.get("/api/v1/players/?search=search")
    assert any(player["initials"] == "SR1" for player in screen_resp.json())

    last_name_resp = await async_client.get("/api/v1/players/?search=alex riley")
    initials = {player["initials"] for player in last_name_resp.json()}
    assert "SR2" in initials


@pytest.mark.asyncio
async def test_initials_must_be_three_capital_alphanumeric(async_client):
    short_resp = await async_client.post(
        "/api/v1/players/",
        json={"initials": "AB", "screen_name": "Tester", "email": "test@example.com"},
    )
    assert short_resp.status_code == 422

    invalid_char_resp = await async_client.post(
        "/api/v1/players/",
        json={"initials": "A$C", "screen_name": "Tester", "email": "test@example.com"},
    )
    assert invalid_char_resp.status_code == 422


@pytest.mark.asyncio
async def test_initials_are_unique_and_suggest_alternatives(async_client):
    first_resp = await async_client.post(
        "/api/v1/players/",
        json={"initials": "abc", "screen_name": "Alpha", "email": "alpha@example.com"},
    )
    assert first_resp.status_code == 200
    assert first_resp.json()["initials"] == "ABC"

    second_resp = await async_client.post(
        "/api/v1/players/",
        json={"initials": "ABC", "screen_name": "Beta", "email": "beta@example.com"},
    )
    assert second_resp.status_code == 400
    detail = second_resp.json()["detail"]
    assert "already taken" in detail["message"]
    assert detail["suggestions"]
    assert all(suggestion.startswith("AB") for suggestion in detail["suggestions"])


@pytest.mark.asyncio
async def test_cannot_update_player_with_duplicate_initials(async_client):
    first_resp = await async_client.post(
        "/api/v1/players/",
        json={"initials": "PIN", "screen_name": "Pin", "email": "pin@example.com"},
    )
    second_resp = await async_client.post(
        "/api/v1/players/",
        json={"initials": "BAL", "screen_name": "Ball", "email": "ball@example.com"},
    )

    update_resp = await async_client.put(
        f"/api/v1/players/{second_resp.json()['id']}",
        json={"initials": "PIN"},
    )

    assert update_resp.status_code == 400
    detail = update_resp.json()["detail"]
    assert "already taken" in detail["message"]
    assert detail["suggestions"]


@pytest.mark.asyncio
async def test_admin_endpoint_requires_auth(async_client):
    response = await async_client.get("/api/v1/admin/players")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_endpoint_exposes_email_with_auth(async_client):
    await async_client.post(
        "/api/v1/players/",
        json={"initials": "ADM", "screen_name": "AdminView", "email": "admin@example.com"},
    )

    credentials = base64.b64encode(b"admin:test-admin").decode()
    response = await async_client.get(
        "/api/v1/admin/players",
        headers={"Authorization": f"Basic {credentials}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert any(player.get("email") == "admin@example.com" for player in payload)


@pytest.mark.asyncio
async def test_admin_page_served(async_client):
    response = await async_client.get("/admin")
    assert response.status_code == 200
    assert "Admin tools" in response.text


@pytest.mark.asyncio
async def test_admin_machine_route_served(async_client):
    response = await async_client.get("/admin/machines/example")
    assert response.status_code == 200
    assert "Machine admin" in response.text
    assert "Machine details" in response.text
    assert "layout layout--single" in response.text
    assert "card" in response.text
    assert "machine-auth-password" not in response.text


@pytest.mark.asyncio
async def test_admin_machine_script_has_no_auto_refresh(async_client):
    response = await async_client.get("/static/js/admin-machine.js")
    assert response.status_code == 200
    assert "setInterval(loadMachine" not in response.text
    assert "GAME_REFRESH_MS" not in response.text


@pytest.mark.asyncio
async def test_discovered_games_hide_stale_entries(async_client):
    fresh_seen = datetime.now(timezone.utc)
    stale_seen = fresh_seen - timedelta(minutes=2)

    async with database.AsyncSessionLocal() as session:
        fresh_machine = models.Machine(
            name="Fresh Game",
            uid="uid-fresh",
            ip_address="10.0.0.1",
            last_seen=fresh_seen,
        )
        stale_machine = models.Machine(
            name="Stale Game",
            uid="uid-stale",
            ip_address="10.0.0.2",
            last_seen=stale_seen,
        )
        session.add_all([fresh_machine, stale_machine])
        await session.flush()

        session.add_all(
            [
                models.Game(machine=fresh_machine, is_active=True),
                models.Game(machine=stale_machine, is_active=True),
            ]
        )
        await session.commit()

    response = await async_client.get("/api/v1/games/discovered")
    assert response.status_code == 200

    games = response.json()
    uids = {game["machine_uid"] for game in games}
    assert "uid-fresh" in uids
    assert "uid-stale" in uids

    assert games[0]["machine_uid"] == "uid-fresh"


@pytest.mark.asyncio
async def test_discovered_games_returns_unique_machines(async_client):
    now = datetime.now(timezone.utc)
    async with database.AsyncSessionLocal() as session:
        machine = models.Machine(
            name="Duplicate Machine",
            uid="dup-machine",
            ip_address="10.0.0.50",
            last_seen=now,
        )
        session.add(machine)
        await session.flush()

        session.add_all(
            [
                models.Game(machine=machine, is_active=True),
                models.Game(machine=machine, is_active=True),
            ]
        )
        await session.commit()

    response = await async_client.get("/api/v1/games/discovered")
    assert response.status_code == 200

    games = [game for game in response.json() if game["machine_uid"] == "dup-machine"]
    assert len(games) == 1


@pytest.mark.asyncio
async def test_discovered_game_includes_version_from_backend(async_client, monkeypatch):
    from api_app import udp

    async def fake_uid(ip_address: str, attempts: int = 2):
        return "uid-version-test"

    async def fake_version(ip_address: str, attempts: int = 2):
        fake_version.calls += 1
        return "9.9.9"

    fake_version.calls = 0

    monkeypatch.setattr(udp, "_fetch_machine_uid", fake_uid)
    monkeypatch.setattr(udp, "_fetch_machine_version", fake_version)

    message = udp.DiscoveryMessage.hello(b"Versioned Game")
    await udp._handle_discovery_message(message, "10.0.0.77")
    await udp._handle_discovery_message(message, "10.0.0.77")

    response = await async_client.get("/api/v1/games/discovered")
    assert response.status_code == 200

    body = response.json()
    versioned = next(entry for entry in body if entry["machine_uid"] == "uid-version-test")
    assert versioned["machine_version"] == "9.9.9"
    assert fake_version.calls == 1


@pytest.mark.asyncio
async def test_machine_listing_deduplicates_by_uid(async_client):
    now = datetime.now(timezone.utc)

    async with database.AsyncSessionLocal() as session:
        earlier = models.Machine(
            name="Old entry",
            uid="dup-uid",
            ip_address="10.0.0.60",
            last_seen=now - timedelta(minutes=20),
        )
        latest = models.Machine(
            name="New entry",
            uid="dup-uid",
            ip_address="10.0.0.61",
            last_seen=now - timedelta(minutes=5),
        )
        session.add_all([earlier, latest])
        await session.commit()

    response = await async_client.get("/api/v1/machines/")
    assert response.status_code == 200

    machines = [machine for machine in response.json() if machine["uid"] == "dup-uid"]
    assert len(machines) == 1
    assert machines[0]["ip_address"] == "10.0.0.61"


@pytest.mark.asyncio
async def test_setting_game_password_requires_auth(async_client):
    games_resp = await async_client.get("/api/v1/games/discovered")
    game_id = games_resp.json()[0]["id"]

    update_resp = await async_client.put(
        f"/api/v1/admin/games/{game_id}/password",
        json={"password": "nope"},
    )

    assert update_resp.status_code == 401


@pytest.mark.asyncio
async def test_leaderboard_uses_seed_data(async_client):
    response = await async_client.get("/api/v1/leaderboard")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3

    nebula = next(game for game in data if game["machine_name"] == "Nebula Orbit")
    assert nebula["leaderboard"][0]["initials"] == "WIZ"
    assert nebula["leaderboard"][0]["score"] == 1240000
    assert nebula["leaderboard"][1]["score"] >= nebula["leaderboard"][2]["score"]

    gravity = next(game for game in data if game["machine_name"] == "Gravity Well")
    assert gravity["leaderboard"][0]["initials"] == "SKY"
    assert gravity["leaderboard"][0]["score"] == 1202000

    solar = next(game for game in data if game["machine_name"] == "Solar Flare")
    assert [entry["initials"] for entry in solar["leaderboard"]] == ["LUX", "NIN", "SKY", "ZEN"]
    assert solar["leaderboard"][0]["score"] == 2240000000000


@pytest.mark.asyncio
async def test_admin_version_refreshes_and_caches(async_client, monkeypatch):
    from api_app import udp

    async def fake_version(ip_address: str, attempts: int = 2):
        fake_version.calls += 1
        return "2.0.0"

    fake_version.calls = 0
    monkeypatch.setattr(udp, "_fetch_machine_version", fake_version)

    async with database.AsyncSessionLocal() as session:
        machine = models.Machine(
            name="Cached",
            ip_address="10.0.0.200",
            uid="cached-version",
            last_seen=datetime.now(timezone.utc),
        )
        session.add(machine)
        await session.flush()
        game = models.Game(machine=machine, is_active=True)
        session.add(game)
        await session.commit()
        await session.refresh(game)
        game_id = game.id

    auth_header = {"Authorization": "Basic " + base64.b64encode(b"admin:test-admin").decode("utf-8")}

    first = await async_client.get(f"/api/v1/admin/games/{game_id}/version", headers=auth_header)
    assert first.status_code == 200
    body = first.json()
    assert body["machine_version"] == "2.0.0"
    assert fake_version.calls == 1

    # Second call should hit cooldown and reuse cached version without another fetch
    second = await async_client.get(f"/api/v1/admin/games/{game_id}/version", headers=auth_header)
    assert second.status_code == 200
    assert fake_version.calls == 1


@pytest.mark.asyncio
async def test_admin_update_checks_are_cached(async_client, monkeypatch):
    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        def json(self):
            return {"version": "9.9.9"}

        @property
        def is_success(self):
            return True

    class FakeClient:
        calls = 0

        async def __aenter__(self):
            FakeClient.calls += 1
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(admin_router, "httpx", type("HttpxStub", (), {"AsyncClient": lambda *_, **__: FakeClient()}))
    admin_router._update_check_cache.clear()

    async with database.AsyncSessionLocal() as session:
        machine = models.Machine(
            name="Updater",
            ip_address="10.0.0.201",
            uid="update-cache",
            last_seen=datetime.now(timezone.utc),
        )
        session.add(machine)
        await session.flush()
        game = models.Game(machine=machine, is_active=True)
        session.add(game)
        await session.commit()
        await session.refresh(game)
        game_id = game.id

    auth_header = {"Authorization": "Basic " + base64.b64encode(b"admin:test-admin").decode("utf-8")}

    first = await async_client.get(f"/api/v1/admin/games/{game_id}/updates/check", headers=auth_header)
    assert first.status_code == 200
    assert FakeClient.calls == 1

    second = await async_client.get(f"/api/v1/admin/games/{game_id}/updates/check", headers=auth_header)
    assert second.status_code == 200
    assert FakeClient.calls == 1


@pytest.mark.asyncio
async def test_applying_update_requires_password(async_client):
    async with database.AsyncSessionLocal() as session:
        machine = models.Machine(
            name="Updater",
            ip_address="10.0.0.202",
            uid="update-password",
            last_seen=datetime.now(timezone.utc),
        )
        session.add(machine)
        await session.flush()
        game = models.Game(machine=machine, is_active=True)
        session.add(game)
        await session.commit()
        await session.refresh(game)
        game_id = game.id

    auth_header = {"Authorization": "Basic " + base64.b64encode(b"admin:test-admin").decode("utf-8")}
    response = await async_client.post(
        f"/api/v1/admin/games/{game_id}/updates/apply",
        json={"url": "https://example.com/update.json"},
        headers=auth_header,
    )

    assert response.status_code == 400
