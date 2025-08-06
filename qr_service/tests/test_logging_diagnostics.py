import importlib
import logging


def test_main_logs_environment(caplog):
    with caplog.at_level(logging.DEBUG):
        import qr_service.service.main as main
        importlib.reload(main)
    messages = [record.getMessage() for record in caplog.records]
    assert any("sys.path=" in message for message in messages)
