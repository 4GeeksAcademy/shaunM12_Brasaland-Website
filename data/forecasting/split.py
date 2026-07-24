"""Temporal train/test split for sales forecasting (context-19)."""

from __future__ import annotations

import pandas as pd

TRAIN_END = pd.Timestamp("2023-12-01")
TEST_START = pd.Timestamp("2024-01-01")

TRAIN_YEARS = 8
TEST_YEARS = 2
TRAIN_YEAR_START = 2016
TRAIN_YEAR_END = 2023
TEST_YEAR_START = 2024
TEST_YEAR_END = 2025


def _month_series(frame: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(frame["month"])


def temporal_train_test_split(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split by calendar date: first 8 years train, last 2 years test.

    Train: 2016-01 through 2023-12 (96 rows).
    Test:  2024-01 through 2025-12 (24 rows).
    """
    months = _month_series(frame)
    train = frame.loc[months <= TRAIN_END].copy()
    test = frame.loc[months >= TEST_START].copy()

    train = train.sort_values("month").reset_index(drop=True)
    test = test.sort_values("month").reset_index(drop=True)
    return train, test


def split_year_sets(
    frame: pd.DataFrame,
) -> tuple[set[int], set[int]]:
    """Return distinct calendar years in train and test partitions."""
    train, test = temporal_train_test_split(frame)
    train_years = set(_month_series(train).dt.year.unique())
    test_years = set(_month_series(test).dt.year.unique())
    return train_years, test_years


def assert_no_split_leakage(train: pd.DataFrame, test: pd.DataFrame) -> None:
    """Raise if train and test share any month timestamps."""
    train_months = set(_month_series(train))
    test_months = set(_month_series(test))
    overlap = train_months & test_months
    if overlap:
        raise ValueError(f"Train/test leakage: shared months {sorted(overlap)}")
