import importlib
import importlib.util
import logging
from pathlib import Path


def test_main_logs_environment(caplog):
    with caplog.at_level(logging.DEBUG):
        import qr_service.service.main as main
        importlib.reload(main)
    messages = [record.getMessage() for record in caplog.records]
    assert any("sys.path=" in message for message in messages)


def test_main_import_fallback(caplog, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root))
    spec = importlib.util.spec_from_file_location("main", root / "service" / "main.py")
    module = importlib.util.module_from_spec(spec)
    with caplog.at_level(logging.DEBUG):
        spec.loader.exec_module(module)
    messages = [record.getMessage() for record in caplog.records]
    assert any("Fallback absolute imports succeeded" in m for m in messages)
