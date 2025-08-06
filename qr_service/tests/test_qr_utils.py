from types import SimpleNamespace
import subprocess
import pytest

from qr_service.service.qr import random_suffix, generate_svg


def test_random_suffix_length():
    assert len(random_suffix(12)) == 12


def test_random_suffix_uniqueness():
    vals = {random_suffix(8) for _ in range(50)}
    assert len(vals) == 50


def test_generate_svg_strips_warnings(monkeypatch):
    def fake_run(cmd, capture_output, check, text):
        return SimpleNamespace(stdout="warn\n<svg></svg>")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert generate_svg("data").startswith("<svg")


def test_generate_svg_raises_without_svg(monkeypatch):
    def fake_run(cmd, capture_output, check, text):
        return SimpleNamespace(stdout="no svg here")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(ValueError):
        generate_svg("data")
