import json
import os
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import Page, sync_playwright

from api_app.main import app


os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin")

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)


def wait_for_fonts(page: Page) -> None:
    page.wait_for_function("document.fonts && document.fonts.status === 'loaded'", timeout=5000)


@pytest.fixture(scope="session")
def live_server():
    config = uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="warning")
    server = uvicorn.Server(config)

    print("[live_server] starting uvicorn thread", flush=True)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    timeout = time.time() + 15
    while not server.started and time.time() < timeout:
        time.sleep(0.1)

    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        pytest.fail("Live server did not start in time")

    print("[live_server] server started", flush=True)

    yield "http://127.0.0.1:8001"

    print("[live_server] teardown begin", flush=True)
    server.should_exit = True
    server.force_exit = True
    thread.join(timeout=5)
    if thread.is_alive():
        print("[live_server] thread still alive after join", flush=True)
        pytest.fail("Live server thread did not shut down")
    print("[live_server] teardown complete", flush=True)


@pytest.fixture()
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context()
        page = context.new_page()
        yield page
        context.close()
        browser.close()


@pytest.mark.playwright
def test_big_screen_grid_fills_viewport(page: Page, live_server: str):
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(f"{live_server}/big-screen", wait_until="networkidle")
    page.wait_for_selector(".game-board")

    measurements = page.evaluate(
        """
        () => {
            const shell = document.querySelector('#big-screen');
            const styles = getComputedStyle(shell);
            const padding = parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom);
            const board = document.querySelector('.board-surface').getBoundingClientRect();
            const screen = shell.getBoundingClientRect();
            return { boardHeight: board.height, screenWidth: screen.width, padding };
        }
        """
    )

    viewport_height = page.evaluate("window.innerHeight")
    viewport_width = page.evaluate("window.innerWidth")
    available_height = viewport_height - measurements["padding"]

    assert available_height - 12 <= measurements["boardHeight"] <= available_height + 6
    assert measurements["screenWidth"] >= viewport_width - 12


@pytest.mark.playwright
@pytest.mark.parametrize("viewport", [(1366, 768), (1280, 720)])
def test_big_screen_padding_scales_on_smaller_viewports(page: Page, live_server: str, viewport: tuple[int, int]):
    width, height = viewport
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{live_server}/big-screen", wait_until="networkidle")
    page.wait_for_selector(".game-board")

    measurements = page.evaluate(
        """
        () => {
            const shell = document.querySelector('#big-screen');
            const styles = getComputedStyle(shell);
            const padding = parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom);
            const board = document.querySelector('.board-surface').getBoundingClientRect();
            return { boardHeight: board.height, padding };
        }
        """
    )

    available_height = height - measurements["padding"]
    doc_height = page.evaluate("document.scrollingElement.scrollHeight")

    assert measurements["boardHeight"] <= available_height + 6
    assert measurements["boardHeight"] >= available_height - 16
    assert doc_height <= height + 10


@pytest.mark.playwright
def test_big_screen_grid_uses_three_columns_and_two_rows(page: Page, live_server: str):
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(f"{live_server}/big-screen", wait_until="networkidle")
    page.wait_for_selector(".board-grid .card")

    columns = page.evaluate(
        "(() => { const active = document.querySelector('.game-board--active .board-grid') || document.querySelector('.board-grid'); return getComputedStyle(active).gridTemplateColumns.split(' ').filter(Boolean).length; })()"
    )
    assert columns == 3

    row_tops = page.evaluate(
        "(() => { const tops = new Set(); const active = document.querySelector('.game-board--active .board-grid') || document.querySelector('.board-grid'); active.querySelectorAll('.card').forEach(card => tops.add(Math.round(card.getBoundingClientRect().top))); return Array.from(tops); })()"
    )

    assert len(row_tops) == 2


@pytest.mark.playwright
def test_leaderboard_has_no_column_headers(page: Page, live_server: str):
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(f"{live_server}/big-screen", wait_until="networkidle")
    page.wait_for_selector(".game-board--active .list__body")

    header = page.query_selector(".game-board--active .list__header")
    assert header is None


@pytest.mark.playwright
def test_component_guide_sections_toggle(page: Page, live_server: str):
    page.goto(f"{live_server}/component-guide", wait_until="networkidle")
    page.wait_for_timeout(200)

    details = page.locator("details.c-accordion__item")
    count = details.count()
    assert count >= 3

    open_states = details.evaluate_all("nodes => nodes.map((node) => node.hasAttribute('open'))")
    assert all(state is False for state in open_states)

    first_summary = details.nth(0).locator("summary")
    first_summary.click()
    page.wait_for_timeout(100)
    assert details.nth(0).evaluate("node => node.hasAttribute('open')")

    first_summary.click()
    page.wait_for_timeout(100)
    assert details.nth(0).evaluate("node => node.hasAttribute('open')") is False


@pytest.mark.playwright
def test_leaderboard_lists_avoid_scrollbars(page: Page, live_server: str):
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(f"{live_server}/big-screen", wait_until="networkidle")
    page.wait_for_selector(".list__body")

    scroll_checks = page.evaluate(
        "() => Array.from(document.querySelectorAll('.list__body')).map(el => ({ scroll: el.scrollHeight, client: el.clientHeight }))"
    )

    assert scroll_checks, "Expected leaderboard lists to be present"
    assert all(entry["scroll"] <= entry["client"] + 2 for entry in scroll_checks)


@pytest.mark.playwright
def test_player_name_chip_matches_score_style(page: Page, live_server: str):
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(f"{live_server}/big-screen", wait_until="networkidle")
    page.wait_for_selector(".game-board--active .player__name.rank")

    style_check = page.evaluate(
        """
        () => {
            const chip = document.querySelector('.game-board--active .player__name.rank');
            const score = document.querySelector('.game-board--active .score__value');
            const chipStyles = getComputedStyle(chip);
            const scoreStyles = getComputedStyle(score);
            return {
                chipBg: chipStyles.backgroundColor,
                scoreBg: scoreStyles.backgroundColor,
                justify: chipStyles.justifyContent,
                textAlign: chipStyles.textAlign,
            };
        }
        """
    )

    assert style_check["chipBg"] == style_check["scoreBg"]
    assert style_check["justify"] == "center"
    assert style_check["textAlign"] == "center"


@pytest.mark.playwright
def test_blank_leaderboard_renders_without_messages(page: Page, live_server: str):
    empty_payload = {
        "games": [
            {
                "machine_name": "Silent Run",
                "champion": None,
                "windows": [
                    {"title": "Weekly", "slug": "game-week", "leaderboard": []},
                    {"title": "Monthly", "slug": "game-month", "leaderboard": []},
                ],
            }
        ]
    }

    page.route(
        "**/api/v1/leaderboard/summary",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(empty_payload),
        ),
    )

    page.goto(f"{live_server}/big-screen", wait_until="networkidle")
    page.wait_for_selector(".game-board")

    empty_messages = page.query_selector_all(".game-board .empty")
    assert len(empty_messages) == 0

    list_body_text = page.evaluate("document.querySelector('.game-board .list__body').textContent.trim()")
    assert list_body_text == ""

    assert page.locator(".champion--empty").count() == 1


@pytest.mark.playwright
def test_big_screen_layout_avoids_page_scroll(page: Page, live_server: str):
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(f"{live_server}/big-screen", wait_until="networkidle")
    page.wait_for_timeout(250)

    doc_height = page.evaluate("document.scrollingElement.scrollHeight")
    viewport_height = page.evaluate("window.innerHeight")
    padding = page.evaluate(
        "() => { const shell = document.querySelector('#big-screen'); const styles = getComputedStyle(shell); return parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom); }"
    )

    assert doc_height <= viewport_height + padding + 6


@pytest.mark.playwright
def test_theme_regression_registration_skin(page: Page, live_server: str):
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(f"{live_server}/register", wait_until="networkidle")
    wait_for_fonts(page)
    page.wait_for_selector(".registration-card")

    tabs = page.locator(".site-nav__link")
    assert tabs.count() >= 3
    assert page.locator(".site-nav__link--current").count() == 1

    buttons = page.locator(".registration-form .wp-btn")
    assert buttons.count() == 2

    page.locator("body").screenshot(path=str(ARTIFACT_DIR / "theme-regression.png"))
    assert (ARTIFACT_DIR / "theme-regression.png").exists()
