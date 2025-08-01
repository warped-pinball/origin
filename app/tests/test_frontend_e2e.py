import os
import sys
import time
import subprocess
from uuid import uuid4
import pytest
from playwright.sync_api import sync_playwright
import httpx


def _start_server(db_path, port):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    subprocess.run([sys.executable, "scripts/build_static.py"], check=True)
    proc = subprocess.Popen(
        ["uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for _ in range(50):
        try:
            httpx.get(f"http://localhost:{port}/", timeout=0.1)
            break
        except Exception:
            time.sleep(0.1)
    return proc


def _stop_server(proc):
    proc.terminate()
    try:
        out, _ = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
    return out


@pytest.fixture
def server(tmp_path):
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
    db_path = tmp_path / "e2e.db"
    proc = _start_server(db_path, port)
    yield f"http://localhost:{port}", proc
    logs = _stop_server(proc)
    print("\n--- server log ---\n" + logs)


def test_signup_and_login_workflow(server):
    """Simulates a user creating an account via the web UI and verifies they are
    automatically logged in. Fails with verbose output so the error message can
    be provided to a language model for troubleshooting."""
    base_url, _ = server
    email = f"test-{uuid4().hex[:8]}@example.com"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        page.click("text=Sign Up")
        page.fill("#signup-email", email)
        page.fill("#signup-screen", "tester")
        page.fill("#signup-password", "pass")
        page.click("#signup-submit")
        page.wait_for_selector("#loggedin-section", timeout=5000)
        # open profile overlay to verify login succeeded
        page.click("#profile-avatar")
        page.wait_for_selector("#account-overlay.show", timeout=2000)
        page.wait_for_timeout(1000)
        page.wait_for_function("document.getElementById('account-screen').value !== ''")
        profile = page.input_value("#account-screen")
        welcome_hidden = page.is_hidden("#welcome-title")
        page.evaluate("document.getElementById('account-close').click()")
        browser.close()
    assert profile == "tester" and welcome_hidden, (
        "Signup flow did not complete correctly or the profile name was not " "loaded."
    )


def test_login_invalid_password_shows_error(server):
    """Ensures that attempting to log in with the wrong password displays an
    error message to the user."""
    base_url, _ = server
    # Create a user directly via API so the login form can be tested
    httpx.post(
        f"{base_url}/api/v1/users/",
        json={"email": "foo@example.com", "password": "right", "screen_name": "foo"},
    ).raise_for_status()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        page.fill("#login-email", "foo@example.com")
        page.fill("#login-password", "wrong")
        page.click("text=Log In")
        page.wait_for_selector("#login-error", timeout=5000)
        err_text = page.text_content("#login-error")
        browser.close()
    assert err_text and "Invalid" in err_text, (
        "Logging in with an incorrect password did not display the expected "
        "error message. Check the server log above and ensure the login form "
        "handles authentication failures correctly."
    )


def test_edit_profile_name(server):
    """Verify that the inline profile name editor updates the displayed name."""
    base_url, _ = server
    # create account via API
    httpx.post(
        f"{base_url}/api/v1/users/",
        json={"email": "edit@example.com", "password": "pass", "screen_name": "old"},
    ).raise_for_status()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        page.fill("#login-email", "edit@example.com")
        page.fill("#login-password", "pass")
        page.click("text=Log In")
        page.wait_for_selector("#loggedin-section", timeout=5000)
        page.click("#profile-avatar")
        page.wait_for_selector("#account-overlay.show")
        page.fill("#account-screen", "new")
        page.wait_for_selector("#account-save", state="visible")
        page.evaluate("document.getElementById('account-save').click()")
        page.wait_for_timeout(500)
        overlay_open = page.eval_on_selector(
            "#account-overlay",
            "el => el.classList.contains('show')",
        )
        updated = page.input_value("#account-screen")
        browser.close()
    assert updated == "new" and overlay_open


def test_navbar_icons_in_order(server):
    """Verify the navbar displays icons in the expected order."""
    base_url, _ = server
    httpx.post(
        f"{base_url}/api/v1/users/",
        json={"email": "nav@example.com", "password": "pass", "screen_name": "nav"},
    ).raise_for_status()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        page.fill("#login-email", "nav@example.com")
        page.fill("#login-password", "pass")
        page.click("text=Log In")
        page.wait_for_selector("#loggedin-section", timeout=5000)
        icons = page.locator("nav#navbar li span").all_text_contents()
        hidden = page.is_hidden("#welcome-title")
        browser.close()
    assert icons == [
        "beenhere",
        "emoji_events",
        "group",
        "settings",
    ] and hidden


def test_navbar_avatar_preserves_aspect_ratio(server):
    """Ensure the navbar avatar keeps its original aspect ratio."""
    base_url, _ = server
    httpx.post(
        f"{base_url}/api/v1/users/",
        json={"email": "ratio@example.com", "password": "pass", "screen_name": "ra"},
    ).raise_for_status()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 320, "height": 720})
        page.goto(base_url)
        page.fill("#login-email", "ratio@example.com")
        page.fill("#login-password", "pass")
        page.click("text=Log In")
        page.wait_for_selector("#loggedin-section", timeout=5000)
        ratio_val = page.eval_on_selector(
            "#profile-avatar",
            "el => el.clientWidth / el.clientHeight"
        )
        browser.close()
    assert 0.95 < ratio_val < 1.05


def test_profile_avatar_uses_webp_with_png_fallback(server):
    """Ensure the profile avatar loads a WebP image with a PNG fallback."""
    base_url, _ = server
    httpx.post(
        f"{base_url}/api/v1/users/",
        json={"email": "webp@example.com", "password": "pass", "screen_name": "webp"},
    ).raise_for_status()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        page.fill("#login-email", "webp@example.com")
        page.fill("#login-password", "pass")
        page.click("text=Log In")
        page.wait_for_selector("#loggedin-section", timeout=5000)
        current_src = page.eval_on_selector(
            "#profile-avatar",
            "img => img.currentSrc",
        )
        fallback_src = page.get_attribute("#profile-avatar", "src")
        browser.close()
    assert "logo.webp" in current_src and fallback_src.endswith("/static/img/logo.png")


def _trigger_install_prompt(page):
    page.evaluate(
        """
        () => {
            const e = new Event('beforeinstallprompt');
            e.preventDefault = () => {};
            e.prompt = () => Promise.resolve();
            e.userChoice = Promise.resolve({ outcome: 'accepted' });
            window.dispatchEvent(e);
        }
        """
    )


def test_install_dialog_not_shown_on_desktop(server):
    base_url, _ = server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        _trigger_install_prompt(page)
        visible = page.is_visible("#install-dialog")
        browser.close()
    assert not visible


def test_install_dialog_shown_on_mobile(server):
    base_url, _ = server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        iphone = p.devices["iPhone 12"]
        context = browser.new_context(**iphone)
        page = context.new_page()
        page.goto(base_url)
        _trigger_install_prompt(page)
        visible = page.is_visible("#install-dialog")
        context.close()
        browser.close()
    assert visible


def test_theme_persistence(server):
    base_url, _ = server
    httpx.post(
        f"{base_url}/api/v1/users/",
        json={"email": "theme@example.com", "password": "pass", "screen_name": "theme"},
    ).raise_for_status()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        page.fill("#login-email", "theme@example.com")
        page.fill("#login-password", "pass")
        page.click("text=Log In")
        page.wait_for_selector("#loggedin-section", timeout=5000)
        page.eval_on_selector("a[data-page='settings']", "el => el.click()")
        page.wait_for_selector("#theme-toggle")
        initial = page.get_attribute("html", "data-theme")
        page.locator("#theme-toggle").scroll_into_view_if_needed()
        page.eval_on_selector("#theme-toggle", "el => el.click()")
        toggled = page.get_attribute("html", "data-theme")
        page.reload()
        persisted = page.get_attribute("html", "data-theme")
        browser.close()
    assert initial != toggled and toggled == persisted
