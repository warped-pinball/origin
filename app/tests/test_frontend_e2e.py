import os
import time
import subprocess
from uuid import uuid4

import pytest
from playwright.sync_api import sync_playwright


def _start_server(db_path, port):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    proc = subprocess.Popen([
        "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"
    ], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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
        welcome = page.text_content("#welcome-title")
        browser.close()
    assert welcome and "Welcome" in welcome, (
        "End-to-end signup flow failed. The page did not show the logged-in "
        "welcome message after account creation. Review the server log above "
        "to identify whether the signup API failed or the UI did not update "
        "correctly.")


def test_login_invalid_password_shows_error(server):
    """Ensures that attempting to log in with the wrong password displays an
    error message to the user."""
    base_url, _ = server
    # Create a user directly via API so the login form can be tested
    subprocess.run([
        "curl", "-s", "-X", "POST", f"{base_url}/api/v1/users/",
        "-H", "Content-Type: application/json",
        "-d", '{"email":"foo@example.com","password":"right","screen_name":"foo"}'
    ], check=True)
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
        "handles authentication failures correctly.")
