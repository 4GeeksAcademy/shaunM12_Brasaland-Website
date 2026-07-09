"""Phase 4 telemetry analysis/report tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import config
import pytest
from fastapi.testclient import TestClient

from telemetry.analysis import consumption_by_location_per_day
from telemetry.analysis import order_failure_rate_per_day


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


def test_consumption_metric_groups_by_date_and_location():
    session = _FakeSession(
        [
            {
                "id": 1,
                "event_type": "consumption_order_created",
                "timestamp": "2026-07-08T10:00:00Z",
                "tags": {"location_id": 3},
            },
            {
                "id": 2,
                "event_type": "consumption_order_created",
                "timestamp": "2026-07-08T11:00:00Z",
                "tags": {"location_id": 3},
            },
            {
                "id": 3,
                "event_type": "consumption_order_created",
                "timestamp": "2026-07-08T12:00:00Z",
                "tags": {"location_id": 11},
            },
            {
                "id": 4,
                "event_type": "consumption_order_created",
                "timestamp": "2026-07-08T13:00:00Z",
                "tags": {},
            },
        ]
    )
    start = datetime(2026, 7, 8, tzinfo=timezone.utc)
    end = datetime(2026, 7, 9, tzinfo=timezone.utc)

    rows = consumption_by_location_per_day(start, end, session=session)

    assert rows == [
        {"date": "2026-07-08", "location_id": 3, "count": 2},
        {"date": "2026-07-08", "location_id": 11, "count": 1},
    ]
    assert session.calls[0]["event_types"] == ["consumption_order_created"]
    assert session.calls[0]["start_date"] == start
    assert session.calls[0]["end_date"] == end


def test_failure_rate_metric_aggregates_per_day():
    session = _FakeSession(
        [
            {
                "id": 11,
                "event_type": "supply_order_created",
                "timestamp": "2026-07-08T09:00:00Z",
                "tags": {},
            },
            {
                "id": 12,
                "event_type": "consumption_order_failed",
                "timestamp": "2026-07-08T10:00:00Z",
                "tags": {},
            },
            {
                "id": 13,
                "event_type": "consumption_order_created",
                "timestamp": "2026-07-08T11:00:00Z",
                "tags": {},
            },
            {
                "id": 14,
                "event_type": "supply_order_failed",
                "timestamp": "2026-07-09T11:00:00Z",
                "tags": {},
            },
        ]
    )
    start = datetime(2026, 7, 8, tzinfo=timezone.utc)
    end = datetime(2026, 7, 10, tzinfo=timezone.utc)

    rows = order_failure_rate_per_day(start, end, session=session)

    assert len(rows) == 2
    assert rows[0]["date"] == "2026-07-08"
    assert rows[0]["total"] == 3
    assert rows[0]["failures"] == 1
    assert rows[0]["failure_rate"] == pytest.approx(1 / 3)
    assert rows[1] == {
        "date": "2026-07-09",
        "total": 1,
        "failures": 1,
        "failure_rate": 1.0,
    }


def test_telemetry_report_uses_cache_for_identical_period(
    anon_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(config, "DATABASE_URL", "")
    import telemetry.routes as routes

    routes._REPORT_CACHE.clear()
    calls = {"consumption": 0, "failure": 0, "auth": 0}

    def _consumption(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        calls["consumption"] += 1
        return [{"date": "2026-07-08", "location_id": 3, "count": 1}]

    def _failure(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        calls["failure"] += 1
        return [{"date": "2026-07-08", "total": 2, "failures": 1, "failure_rate": 0.5}]

    def _auth(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        calls["auth"] += 1
        return [{"date": "2026-07-08", "total": 2, "failed": 1, "failure_rate": 0.5}]

    monkeypatch.setattr(routes, "consumption_by_location_per_day", _consumption)
    monkeypatch.setattr(routes, "order_failure_rate_per_day", _failure)
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
    assert calls == {"consumption": 1, "failure": 1, "auth": 1}


def test_telemetry_report_rejects_invalid_period(anon_client: TestClient):
    response = anon_client.get(
        "/telemetry/report?"
        "start_date=2026-07-15T00:00:00Z&end_date=2026-07-08T00:00:00Z"
    )
    assert response.status_code == 422

