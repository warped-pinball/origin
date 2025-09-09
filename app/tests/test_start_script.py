import pathlib


def test_uvicorn_runs_foreground():
    script = pathlib.Path("scripts/start.sh").read_text().splitlines()
    lines = [
        line.strip()
        for line in script
        if "uvicorn app.main:app" in line and not line.strip().startswith("#")
    ]
    assert lines, "uvicorn launch line not found"
    assert not any(
        line.endswith("&") for line in lines
    ), "uvicorn should run in foreground"
