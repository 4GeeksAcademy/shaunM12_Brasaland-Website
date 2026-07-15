"""Unit tests for weekly location KPI transforms (no database)."""

from __future__ import annotations

from datetime import datetime, timezone

from data.process.weekly_location_kpis import (
    compute_weekly_kpis,
    iso_week_start_utc,
    transform_purchase_cost,
    events_to_frame,
)


def test_iso_week_start_is_monday_utc():
    ts = datetime(2026, 7, 14, 15, 0, tzinfo=timezone.utc)  # Tuesday
    assert iso_week_start_utc(ts).isoformat() == "2026-07-13"


def test_purchase_and_waste_skip_missing_unit_cost():
    rows = [
        {
            "id": 1,
            "event_type": "inbound_order_created",
            "timestamp": datetime(2026, 7, 14, 10, tzinfo=timezone.utc),
            "tags": {
                "location_id": 1,
                "country": "CO",
                "currency": "COP",
                "quantity": 10,
                "unit_cost": 100,
            },
        },
        {
            "id": 2,
            "event_type": "inbound_order_created",
            "timestamp": datetime(2026, 7, 14, 11, tzinfo=timezone.utc),
            "tags": {
                "location_id": 1,
                "country": "CO",
                "currency": "COP",
                "quantity": 5,
                # missing unit_cost → skip
            },
        },
        {
            "id": 3,
            "event_type": "stock_waste_registered",
            "timestamp": datetime(2026, 7, 14, 12, tzinfo=timezone.utc),
            "tags": {
                "location_id": 1,
                "country": "CO",
                "currency": "COP",
                "quantity": 2,
                "unit_cost": 100,
            },
        },
        {
            "id": 4,
            "event_type": "stock_waste_registered",
            "timestamp": datetime(2026, 7, 14, 13, tzinfo=timezone.utc),
            "tags": {
                "location_id": 1,
                "country": "CO",
                "currency": "COP",
                "quantity": 1,
                # missing unit_cost → skip
            },
        },
        {
            "id": 5,
            "event_type": "stock_threshold_triggered",
            "timestamp": datetime(2026, 7, 14, 14, tzinfo=timezone.utc),
            "tags": {"location_id": 1, "country": "CO", "currency": "COP"},
        },
        {
            "id": 6,
            "event_type": "ingredient_price_variance_detected",
            "timestamp": datetime(2026, 7, 15, 9, tzinfo=timezone.utc),
            "tags": {"location_id": 1, "country": "CO", "currency": "COP"},
        },
    ]

    frame, skipped = compute_weekly_kpis(rows)
    assert skipped == 2
    assert len(frame) == 1
    row = frame.iloc[0]
    assert int(row["location_id"]) == 1
    assert float(row["total_purchase_cost"]) == 1000.0
    assert float(row["total_waste_cost"]) == 200.0
    assert float(row["waste_ratio"]) == 0.2
    assert int(row["stockout_events_count"]) == 1
    assert int(row["price_alert_events_count"]) == 1


def test_sparse_no_row_for_inactive_location():
    rows = [
        {
            "id": 1,
            "event_type": "stock_threshold_triggered",
            "timestamp": datetime(2026, 7, 14, 10, tzinfo=timezone.utc),
            "tags": {"location_id": 3, "country": "CO", "currency": "COP"},
        }
    ]
    frame, skipped = compute_weekly_kpis(rows)
    assert skipped == 0
    assert list(frame["location_id"].astype(int)) == [3]


def test_waste_ratio_zero_when_no_purchases():
    rows = [
        {
            "id": 1,
            "event_type": "stock_waste_registered",
            "timestamp": datetime(2026, 7, 14, 10, tzinfo=timezone.utc),
            "tags": {
                "location_id": 11,
                "country": "US",
                "currency": "USD",
                "quantity": 1,
                "unit_cost": 5,
            },
        }
    ]
    frame, _ = compute_weekly_kpis(rows)
    assert float(frame.iloc[0]["waste_ratio"]) == 0.0
    assert float(frame.iloc[0]["total_waste_cost"]) == 5.0


def test_transform_purchase_cost_unit():
    rows = [
        {
            "id": 1,
            "event_type": "inbound_order_created",
            "timestamp": datetime(2026, 7, 13, 1, tzinfo=timezone.utc),
            "tags": {
                "location_id": 10,
                "quantity": 2,
                "unit_cost": 12.5,
            },
        }
    ]
    purchase, skipped = transform_purchase_cost(events_to_frame(rows))
    assert skipped == 0
    assert float(purchase.iloc[0]["total_purchase_cost"]) == 25.0
    assert purchase.iloc[0]["currency"] == "USD"
