from pathlib import Path

from scripts.market_share_mpu import (
    apply_corrections,
    identify_outliers,
    load_machines,
    market_share,
)

DATA_FILE = Path(__file__).parent / "data" / "machines.csv"


def test_identify_outliers():
    machines = load_machines(DATA_FILE)
    outliers = identify_outliers(machines)

    assert "Spike 2" in outliers
    spike = outliers["Spike 2"]
    assert {m.title for m in spike["cross_manufacturer"]} == {"Baz", "Qux"}
    assert spike["year_outliers"] == []

    assert "System 11" in outliers
    system11 = outliers["System 11"]
    assert {m.title for m in system11["cross_manufacturer"]} == {"Gamma"}
    assert {m.title for m in system11["year_outliers"]} == {"Delta"}


def test_market_share_after_corrections():
    machines = load_machines(DATA_FILE)
    outliers = identify_outliers(machines)
    corrected = apply_corrections(machines, outliers)
    report = market_share(corrected)
    # Convert to dict for easier assertions
    lookup = {(r["mpu"], r["manufacturer"]): r for r in report}

    assert lookup[("Spike 2", "Stern")]["count"] == 4
    assert ("Spike 2", "Gottlieb") not in lookup
    assert lookup[("System 11", "Williams")]["count"] == 4
