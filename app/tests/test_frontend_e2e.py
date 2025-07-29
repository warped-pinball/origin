import os
import time
import subprocess
from uuid import uuid4

import pytest
from playwright.sync_api import sync_playwright


def _start_server(db_path, port):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    proc = subprocess.Popen(
        ["uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(2)
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
    port = 8001
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
        # open profile page to verify login succeeded
        page.click("li[data-page='account'] a")
        page.wait_for_selector("#profile-name-text", timeout=2000)
        profile = page.text_content("#profile-name-text")
        welcome_hidden = page.is_hidden("#welcome-title")
        browser.close()
    assert profile == "tester" and welcome_hidden, (
        "Signup flow did not complete correctly or the profile name was not " "loaded."
    )


def test_login_invalid_password_shows_error(server):
    """Ensures that attempting to log in with the wrong password displays an
    error message to the user."""
    base_url, _ = server
    # Create a user directly via API so the login form can be tested
    subprocess.run(
        [
            "curl",
            "-s",
            "-X",
            "POST",
            f"{base_url}/api/v1/users/",
            "-H",
            "Content-Type: application/json",
            "-d",
            '{"email":"foo@example.com","password":"right","screen_name":"foo"}',
        ],
        check=True,
    )
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
    subprocess.run(
        [
            "curl",
            "-s",
            "-X",
            "POST",
            f"{base_url}/api/v1/users/",
            "-H",
            "Content-Type: application/json",
            "-d",
            '{"email":"edit@example.com","password":"pass","screen_name":"old"}',
        ],
        check=True,
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        page.fill("#login-email", "edit@example.com")
        page.fill("#login-password", "pass")
        page.click("text=Log In")
        page.wait_for_selector("#loggedin-section", timeout=5000)
        page.click("li[data-page='account'] a")
        page.wait_for_selector("#edit-name-btn")
        page.click("#edit-name-btn")
        page.fill("#account-screen", "new")
        page.click("#edit-name-form button[type='submit']")
        page.wait_for_function("document.querySelector('#profile-name-text').textContent === 'new'")
        updated = page.text_content("#profile-name-text")
        browser.close()
    assert updated == "new"


def test_nav_label_trophies(server):
    """Ensure the navigation bar shows 'Trophies' instead of 'Achievements'."""
    base_url, _ = server
    subprocess.run(
        [
            "curl",
            "-s",
            "-X",
            "POST",
            f"{base_url}/api/v1/users/",
            "-H",
            "Content-Type: application/json",
            "-d",
            '{"email":"nav@example.com","password":"pass","screen_name":"nav"}',
        ],
        check=True,
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        page.fill("#login-email", "nav@example.com")
        page.fill("#login-password", "pass")
        page.click("text=Log In")
        page.wait_for_selector("#loggedin-section", timeout=5000)
        label = page.text_content("li[data-page='achievements'] small")
        hidden = page.is_hidden("#welcome-title")
        browser.close()
    assert label == "Trophies" and hidden
