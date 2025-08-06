import json
import subprocess
import shutil
from pathlib import Path

import pytest

SERVICE_DIR = Path(__file__).resolve().parents[1] / "service"


def _ensure_dependencies() -> None:
    if not (SERVICE_DIR / "node_modules").exists():
        subprocess.run(["npm", "install"], cwd=SERVICE_DIR, check=True)


@pytest.mark.integration
def test_generate_js_outputs_svg():
    if shutil.which("node") is None or shutil.which("npm") is None:
        pytest.skip("node or npm is not installed")
    _ensure_dependencies()
    opts = {
        "width": 100,
        "height": 100,
        "type": "svg",
        "data": "test",
        "backgroundOptions": {"color": "#ffffff"},
        "dotsOptions": {"color": "#000000"},
        "cornersSquareOptions": {"color": "#000000"},
    }
    res = subprocess.run(
        ["node", "generate.js", json.dumps(opts)],
        cwd=SERVICE_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "<svg" in res.stdout
