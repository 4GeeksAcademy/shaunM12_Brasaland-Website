#!/usr/bin/env python3
"""
Incident File Analyzer — Phase 1 analysis script.

Install dependencies:
    pip install -r scripts/requirements.txt

Usage:
    python scripts/analyze.py incidents-brasaland.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from incident_analyzer.core import (  # noqa: E402
    analyze_dataframe,
    build_results_rows,
    format_summary,
    load_csv_bytes,
)
import pandas as pd  # noqa: E402


def load_incidents(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    payload = path.read_bytes()
    return load_csv_bytes(payload)


def export_results(result: dict, output_path: Path) -> None:
    rows = build_results_rows(result)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    print(f"Results exported to {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze Brasaland incident CSV files and print a summary."
    )
    parser.add_argument(
        "csv_path",
        help="Path to the incident CSV file (e.g. incidents-brasaland.csv)",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    try:
        df = load_incidents(csv_path)
        result = analyze_dataframe(df, str(csv_path))
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(format_summary(result))

    try:
        answer = input("Export results to CSV? [y / n]: ").strip().lower()
    except EOFError:
        answer = "n"

    if answer in {"y", "yes"}:
        export_results(result, Path("results.csv"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
