"""Utilities for analyzing market share by MPU and detecting data outliers.

This module provides a small toolkit that loads machine metadata from a CSV file,
identifies questionable records (such as MPUs that span multiple manufacturers
or titles far outside the typical production year), and produces a market share
summary.  The goal is to make it easy to spot entries that likely need
additional research.

The CSV is expected to have the following columns:
    title, manufacturer, mpu, year

Example usage:
    from scripts.market_share_mpu import load_machines, identify_outliers,
        apply_corrections, market_share
    machines = load_machines('machines.csv')
    outliers = identify_outliers(machines)
    corrected = apply_corrections(machines, outliers)
    report = market_share(corrected)
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List
import csv


@dataclass
class Machine:
    """Simple representation of a pinball machine for analysis."""

    title: str
    manufacturer: str
    mpu: str
    year: int


def load_machines(path: Path | str) -> List[Machine]:
    """Load machines from a CSV file."""
    path = Path(path)
    machines: List[Machine] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                machines.append(
                    Machine(
                        title=row["title"].strip(),
                        manufacturer=row["manufacturer"].strip(),
                        mpu=row["mpu"].strip(),
                        year=int(row["year"]),
                    )
                )
            except (KeyError, ValueError) as exc:  # pragma: no cover - defensive
                raise ValueError(f"Invalid row in {path}: {row}") from exc
    return machines


def identify_outliers(machines: Iterable[Machine], year_threshold: int = 5) -> Dict[str, Dict[str, List[Machine]]]:
    """Identify machines that look suspicious within each MPU group.

    Returns a dictionary keyed by MPU.  Each value contains:
        - 'majority_manufacturer': the most common manufacturer for the MPU
        - 'cross_manufacturer': list of machines whose manufacturer differs
        - 'year_outliers': list of machines whose year differs greatly from the
          median year for that MPU (difference > year_threshold)
    """
    mpus: Dict[str, List[Machine]] = defaultdict(list)
    for m in machines:
        mpus[m.mpu].append(m)

    outliers: Dict[str, Dict[str, List[Machine]]] = {}
    for mpu, group in mpus.items():
        manufacturer_counts = Counter(m.manufacturer for m in group)
        majority_manufacturer, _ = manufacturer_counts.most_common(1)[0]
        cross_manufacturer = [m for m in group if m.manufacturer != majority_manufacturer]

        # Determine the typical production year based on the majority manufacturer
        majority_years = [m.year for m in group if m.manufacturer == majority_manufacturer]
        med_year = median(majority_years)
        year_outliers = [m for m in group if abs(m.year - med_year) > year_threshold]

        if cross_manufacturer or year_outliers:
            outliers[mpu] = {
                "majority_manufacturer": majority_manufacturer,
                "cross_manufacturer": cross_manufacturer,
                "year_outliers": [m for m in year_outliers if m not in cross_manufacturer],
            }
    return outliers


def apply_corrections(machines: List[Machine], outliers: Dict[str, Dict[str, List[Machine]]]) -> List[Machine]:
    """Apply simple corrections by aligning cross-manufacturer titles with the
    majority manufacturer for their MPU.

    The function returns a new list so the original data remains unchanged."""
    corrected: List[Machine] = []
    for m in machines:
        info = outliers.get(m.mpu)
        if info and any(m.title == cm.title for cm in info["cross_manufacturer"]):
            corrected.append(
                Machine(
                    title=m.title,
                    manufacturer=info["majority_manufacturer"],
                    mpu=m.mpu,
                    year=m.year,
                )
            )
        else:
            corrected.append(m)
    return corrected


def market_share(machines: Iterable[Machine], minimum_share: float = 0.01) -> List[Dict[str, object]]:
    """Compute market share by MPU and manufacturer.

    Only manufacturers whose total share across all machines is >= ``minimum_share``
    are considered.  The return value is a list of dictionaries sorted by MPU
    and manufacturer.
    """
    machines = list(machines)
    total = len(machines)
    manufacturer_totals = Counter(m.manufacturer for m in machines)
    allowed_manufacturers = {
        mfg for mfg, count in manufacturer_totals.items() if count / total >= minimum_share
    }

    mpu_totals: Dict[str, Counter] = defaultdict(Counter)
    for m in machines:
        if m.manufacturer in allowed_manufacturers:
            mpu_totals[m.mpu][m.manufacturer] += 1

    rows: List[Dict[str, object]] = []
    for mpu in sorted(mpu_totals):
        for manufacturer, count in mpu_totals[mpu].most_common():
            rows.append(
                {
                    "mpu": mpu,
                    "manufacturer": manufacturer,
                    "count": count,
                    "share": count / total,
                }
            )
    return rows


def main(path: str) -> None:  # pragma: no cover - convenience CLI
    machines = load_machines(path)
    outliers = identify_outliers(machines)
    if outliers:
        print("Potential issues detected:")
        for mpu, info in outliers.items():
            print(f"\nMPU: {mpu}")
            if info["cross_manufacturer"]:
                print("  Cross-manufacturer titles:")
                for m in info["cross_manufacturer"]:
                    print(f"    - {m.title} ({m.manufacturer})")
            if info["year_outliers"]:
                print("  Year outliers:")
                for m in info["year_outliers"]:
                    print(f"    - {m.title} ({m.year})")

    corrected = apply_corrections(machines, outliers)
    report = market_share(corrected)
    print("\nMarket share by MPU after corrections:")
    for row in report:
        print(
            f"{row['mpu']:<15} {row['manufacturer']:<15} {row['count']:>3} "
            f"({row['share']*100:5.2f}% share)"
        )


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Analyze market share by MPU")
    parser.add_argument("path", help="CSV file containing machine data")
    args = parser.parse_args()
    main(args.path)
