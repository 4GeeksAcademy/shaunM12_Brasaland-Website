"""Feature engineering for sales forecasting (context-19)."""

from __future__ import annotations

import pandas as pd

TARGET_COLUMN = "revenue_usd"

FEATURE_COLUMNS = (
    "calendar_month",
    "months_since_start",
    "revenue_lag_1",
    "revenue_lag_3",
    "revenue_lag_12",
)

LAG_PERIODS = (1, 3, 12)


def build_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Build calendar and lagged-revenue features on the full timeline.

    Lags use only prior months (one-step-ahead safe). Rows with NaN lags are dropped.
    """
    data = frame.sort_values("month").copy()
    data["month_ts"] = pd.to_datetime(data["month"])
    start = data["month_ts"].min()
    data["calendar_month"] = data["month_ts"].dt.month.astype(int)
    data["months_since_start"] = (
        (data["month_ts"].dt.year - start.year) * 12 + (data["month_ts"].dt.month - 1)
    ).astype(int)

    for lag in LAG_PERIODS:
        data[f"revenue_lag_{lag}"] = data[TARGET_COLUMN].shift(lag)

    data = data.dropna(subset=list(FEATURE_COLUMNS)).reset_index(drop=True)
    return data


def feature_matrix(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Return ``X``, ``y``, and ``month`` series from a featured frame."""
    missing = [col for col in FEATURE_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"Featured frame missing columns: {missing}")
    if TARGET_COLUMN not in frame.columns:
        raise ValueError(f"Featured frame missing target: {TARGET_COLUMN}")

    x_frame = frame[list(FEATURE_COLUMNS)].copy()
    y = frame[TARGET_COLUMN].astype(float).copy()
    months = pd.to_datetime(frame["month"]).copy()
    return x_frame, y, months
