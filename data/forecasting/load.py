"""Load and validate Brasaland monthly sales CSV (context-19)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SALES_CSV = _REPO_ROOT / "data" / "raw" / "brasaland_sales.csv"

EXPECTED_COLUMNS = (
    "month",
    "revenue_usd",
    "covers_served",
    "avg_ticket_usd",
    "market",
)

EXPECTED_ROW_COUNT = 120
EXPECTED_START = pd.Timestamp("2016-01-01")
EXPECTED_END = pd.Timestamp("2025-12-01")
EXPECTED_MARKET = "consolidated"


def default_sales_csv_path() -> Path:
    return DEFAULT_SALES_CSV


def load_sales(csv_path: Path | str | None = None) -> pd.DataFrame:
    """Load ``brasaland_sales.csv`` and validate schema per CONTEXT-brasaland."""
    path = Path(csv_path) if csv_path is not None else DEFAULT_SALES_CSV
    if not path.is_file():
        raise FileNotFoundError(f"Sales dataset not found: {path}")

    frame = pd.read_csv(path)
    validate_sales_frame(frame)
    return frame


def validate_sales_frame(frame: pd.DataFrame) -> None:
    """Fail fast if the frame does not match the locked dataset contract."""
    missing = [col for col in EXPECTED_COLUMNS if col not in frame.columns]
    extra = [col for col in frame.columns if col not in EXPECTED_COLUMNS]
    if missing:
        raise ValueError(f"Sales CSV missing columns: {missing}")
    if extra:
        raise ValueError(f"Sales CSV has unexpected columns: {extra}")

    if len(frame) != EXPECTED_ROW_COUNT:
        raise ValueError(
            f"Sales CSV expected {EXPECTED_ROW_COUNT} rows, got {len(frame)}"
        )

    if frame.isnull().any().any():
        raise ValueError("Sales CSV contains null values")

    months = pd.to_datetime(frame["month"], errors="coerce")
    if months.isnull().any():
        raise ValueError("Sales CSV contains invalid month values")

    ordered = months.sort_values().reset_index(drop=True)
    if not ordered.is_monotonic_increasing:
        raise ValueError("Sales CSV month column must be sortable in chronological order")

    if ordered.iloc[0] != EXPECTED_START or ordered.iloc[-1] != EXPECTED_END:
        raise ValueError(
            f"Sales CSV date span must be {EXPECTED_START.date()} to {EXPECTED_END.date()}"
        )

    # One row per calendar month, no gaps (2016-01 through 2025-12).
    expected_index = pd.date_range(EXPECTED_START, EXPECTED_END, freq="MS")
    if len(ordered.unique()) != len(expected_index):
        raise ValueError("Sales CSV must have exactly one row per month with no gaps")
    if not ordered.dt.to_period("M").tolist() == expected_index.to_period("M").tolist():
        raise ValueError("Sales CSV month sequence does not match expected monthly range")

    markets = frame["market"].astype(str).unique().tolist()
    if markets != [EXPECTED_MARKET]:
        raise ValueError(
            f"Sales CSV market column must be only '{EXPECTED_MARKET}', got {markets}"
        )
