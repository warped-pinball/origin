import importlib


def test_machines_module_imports():
    importlib.import_module("app.routers.machines")
