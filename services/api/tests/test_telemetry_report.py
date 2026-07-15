"""Phase 4 telemetry analysis/report tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import config
import pytest
from fastapi.testclient import TestClient

from telemetry.analysis import daily_consumption_by_product_and_location
from telemetry.analysis import stock_out_frequency
from telemetry.analysis import waste_loss_ratio


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def mappings(self) -> "_FakeResult":
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeSession:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self.calls: list[dict[str, Any]] = []

    def execute(self, _statement: Any, params: dict[str, Any]) -> _FakeResult:
        self.calls.append(params)
        return _FakeResult(self.rows)


def test_daily_consumption_metric_sums_quantity_by_product_and_location():
    session = _FakeSession(
        [
            {
                "id": 1,
                "event_type": "outbound_order_created",
                "timestamp": "2026-07-08T10:00:00Z",
                "tags": {
                    "location_id": 3,
                    "product_id": 7,
                    "quantity": 10,
                },
            },
            {
                "id": 2,
                "event_type": "outbound_order_created",
                "timestamp": "2026-07-08T11:00:00Z",
                "tags": {
                    "location_id": 3,
                    "product_id": 7,
                    "quantity": 5,
                },
            },
            {
                "id": 4,
                "event_type": "outbound_order_created",
                "timestamp": "2026-07-08T13:00:00Z",
                "tags": {"location_id": 11, "product_id": 2, "quantity": 8},
            },
        ]
    )
    start = datetime(2026, 7, 8, tzinfo=timezone.utc)
    end = datetime(2026, 7, 9, tzinfo=timezone.utc)

    rows = daily_consumption_by_product_and_location(start, end, session=session)

    assert rows == [
        {"date": "2026-07-08", "product_id": 7, "location_id": 3, "quantity": 15.0},
        {"date": "2026-07-08", "product_id": 2, "location_id": 11, "quantity": 8.0},
    ]
    assert session.calls[0]["event_types"] == ["outbound_order_created"]


def test_stock_out_frequency_counts_threshold_and_insufficient_stock_only():
    session = _FakeSession(
        [
            {
                "id": 11,
                "event_type": "stock_threshold_triggered",
                "timestamp": "2026-07-08T09:00:00Z",
                "tags": {"location_id": 3, "product_id": 7},
            },
            {
                "id": 12,
                "event_type": "outbound_order_failed",
                "timestamp": "2026-07-08T10:00:00Z",
                "tags": {
                    "location_id": 3,
                    "product_id": 7,
                    "error_code": "insufficient_stock",
                },
            },
            {
                "id": 13,
                "event_type": "outbound_order_failed",
                "timestamp": "2026-07-08T11:00:00Z",
                "tags": {
                    "location_id": 3,
                    "product_id": 7,
                    "error_code": "validation_error",
                },
            },
            {
                "id": 14,
                "event_type": "stock_threshold_triggered",
                "timestamp": "2026-07-09T11:00:00Z",
                "tags": {"location_id": 11, "product_id": 2},
            },
        ]
    )
    start = datetime(2026, 7, 8, tzinfo=timezone.utc)
    end = datetime(2026, 7, 10, tzinfo=timezone.utc)

    rows = stock_out_frequency(start, end, session=session)

    assert rows == [
        {"date": "2026-07-08", "product_id": 7, "location_id": 3, "count": 2},
        {"date": "2026-07-09", "product_id": 2, "location_id": 11, "count": 1},
    ]


def test_waste_loss_ratio_computes_waste_over_total_per_location():
    session = _FakeSession(
        [
            {
                "id": 21,
                "event_type": "outbound_order_created",
                "timestamp": "2026-07-08T09:00:00Z",
                "tags": {"location_id": 3, "quantity": 10},
            },
            {
                "id": 22,
                "event_type": "stock_waste_registered",
                "timestamp": "2026-07-08T10:00:00Z",
                "tags": {"location_id": 3, "quantity": 5, "reason": "unspecified"},
            },
            {
                "id": 23,
                "event_type": "outbound_order_created",
                "timestamp": "2026-07-08T11:00:00Z",
                "tags": {"location_id": 11, "quantity": 8},
            },
        ]
    )
    start = datetime(2026, 7, 8, tzinfo=timezone.utc)
    end = datetime(2026, 7, 9, tzinfo=timezone.utc)

    rows = waste_loss_ratio(start, end, session=session)

    assert len(rows) == 2
    location_3 = next(row for row in rows if row["location_id"] == 3)
    assert location_3["waste_quantity"] == 5.0
    assert location_3["total_quantity"] == 15.0
    assert location_3["ratio"] == pytest.approx(5 / 15)


def test_telemetry_report_uses_cache_for_identical_period(
    anon_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(config, "DATABASE_URL", "")
    import telemetry.routes as routes

    routes._REPORT_CACHE.clear()
    calls = {"kpi1": 0, "kpi2": 0, "kpi3": 0, "auth": 0}

    def _kpi1(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        calls["kpi1"] += 1
        return [{"date": "2026-07-08", "product_id": 7, "location_id": 3, "quantity": 1.0}]

    def _kpi2(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        calls["kpi2"] += 1
        return [{"date": "2026-07-08", "product_id": 7, "location_id": 3, "count": 1}]

    def _kpi3(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        calls["kpi3"] += 1
        return [
            {
                "date": "2026-07-08",
                "location_id": 3,
                "waste_quantity": 1.0,
                "total_quantity": 4.0,
                "ratio": 0.25,
            }
        ]

    def _auth(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        calls["auth"] += 1
        return [{"date": "2026-07-08", "total": 2, "failed": 1, "failure_rate": 0.5}]

    monkeypatch.setattr(routes, "daily_consumption_by_product_and_location", _kpi1)
    monkeypatch.setattr(routes, "stock_out_frequency", _kpi2)
    monkeypatch.setattr(routes, "waste_loss_ratio", _kpi3)
    monkeypatch.setattr(routes, "auth_failure_rate_per_day", _auth)
    period = (
        "/telemetry/report?"
        "start_date=2026-07-08T00:00:00Z&end_date=2026-07-15T00:00:00Z"
    )

    first = anon_client.get(period)
    second = anon_client.get(period)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert "daily_consumption_by_product_and_location" in first.json()["metrics"]
    assert calls == {"kpi1": 1, "kpi2": 1, "kpi3": 1, "auth": 1}


def test_telemetry_report_rejects_invalid_period(anon_client: TestClient):
    response = anon_client.get(
        "/telemetry/report?"
        "start_date=2026-07-15T00:00:00Z&end_date=2026-07-08T00:00:00Z"
    )
    assert response.status_code == 422
