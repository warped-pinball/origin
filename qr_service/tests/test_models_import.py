import importlib
import sys
from pathlib import Path


def test_models_top_level_import():
    package_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(package_dir))
    try:
        mod = importlib.import_module('models')
        assert hasattr(mod, 'QRCode')
    finally:
        sys.path.pop(0)
        if 'models' in sys.modules:
            del sys.modules['models']
