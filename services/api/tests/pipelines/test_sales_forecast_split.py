"""Sales forecast split tests (context-19): 8-year train / 2-year test, no leakage."""

from __future__ import annotations

import pandas as pd

from data.forecasting.load import load_sales
from data.forecasting.split import (
    TEST_START,
    TEST_YEAR_END,
    TEST_YEAR_START,
    TEST_YEARS,
    TRAIN_END,
    TRAIN_YEAR_END,
    TRAIN_YEAR_START,
    TRAIN_YEARS,
    assert_no_split_leakage,
    split_year_sets,
    temporal_train_test_split,
)


def test_load_sales_matches_context_contract():
    frame = load_sales()
    assert len(frame) == 120
    assert list(frame.columns) == [
        "month",
        "revenue_usd",
        "covers_served",
        "avg_ticket_usd",
        "market",
    ]


def test_temporal_split_respects_eight_two_year_rule():
    frame = load_sales()
    train, test = temporal_train_test_split(frame)
    train_years, test_years = split_year_sets(frame)

    assert len(train) == 96
    assert len(test) == 24
    assert len(train_years) == TRAIN_YEARS
    assert len(test_years) == TEST_YEARS
    assert train_years == set(range(TRAIN_YEAR_START, TRAIN_YEAR_END + 1))
    assert test_years == set(range(TEST_YEAR_START, TEST_YEAR_END + 1))

    train_months = pd.to_datetime(train["month"])
    test_months = pd.to_datetime(test["month"])

    assert train_months.min() == pd.Timestamp("2016-01-01")
    assert train_months.max() == TRAIN_END
    assert test_months.min() == TEST_START
    assert test_months.max() == pd.Timestamp("2025-12-01")


def test_no_date_overlap_between_train_and_test():
    frame = load_sales()
    train, test = temporal_train_test_split(frame)

    train_dates = set(pd.to_datetime(train["month"]))
    test_dates = set(pd.to_datetime(test["month"]))

    assert train_dates.isdisjoint(test_dates)
    assert_no_split_leakage(train, test)


def test_split_rejects_invalid_boundary_on_synthetic_frame():
    """Rows after TRAIN_END must never appear in train."""
    frame = load_sales()
    train, test = temporal_train_test_split(frame)

    assert pd.to_datetime(train["month"]).max() < TEST_START
    assert pd.to_datetime(test["month"]).min() >= TEST_START


def test_temporal_split_on_minimal_synthetic_months():
    """Unit coverage without relying on full CSV beyond load tests."""
    months = pd.date_range("2016-01-01", "2025-12-01", freq="MS")
    frame = pd.DataFrame(
        {
            "month": months.strftime("%Y-%m-%d"),
            "revenue_usd": range(len(months)),
            "covers_served": 1,
            "avg_ticket_usd": 1.0,
            "market": "consolidated",
        }
    )
    train, test = temporal_train_test_split(frame)
    assert len(train) == 96
    assert len(test) == 24
    assert_no_split_leakage(train, test)
