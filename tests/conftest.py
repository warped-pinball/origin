"""Global Pytest configuration for diagnostics."""

import asyncio
import sys
import threading
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from api_app.database import engine


def _thread_snapshot() -> str:
    threads = [
        f"{t.name}(daemon={t.daemon})"
        for t in threading.enumerate()
        if t is not threading.main_thread()
    ]
    return ", ".join(sorted(threads)) or "none"


def _log_marker(label: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(
        f"[pytest-marker] {label} at {timestamp} | threads: {_thread_snapshot()}",
        flush=True,
    )


def pytest_sessionstart(session):
    _log_marker("session start")


def pytest_sessionfinish(session, exitstatus):
    _log_marker(f"session finish exitstatus={exitstatus}")
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(engine.dispose())
    finally:
        loop.close()
    _log_marker("session finish post-dispose")


def pytest_unconfigure(config):
    _log_marker("pytest unconfigure")
