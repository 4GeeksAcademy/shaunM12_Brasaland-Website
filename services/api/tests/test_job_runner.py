"""Unit tests for DEV-53 job_runner helpers (no live DB required)."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from job_runner.export import CSV_COLUMNS, telemetry_csv_path, utc_day_bounds
from job_runner.schedule import seconds_until_next_run


def test_utc_day_bounds_half_open():
    start, end = utc_day_bounds(date(2026, 7, 14))
    assert start.isoformat() == "2026-07-14T00:00:00+00:00"
    assert end.isoformat() == "2026-07-15T00:00:00+00:00"


def test_telemetry_csv_path_format(tmp_path: Path):
    path = telemetry_csv_path(tmp_path, date(2026, 7, 14))
    assert path.name == "telemetry_2026-07-14.csv"
    assert path.parent == tmp_path


def test_csv_columns_stable():
    assert "event_type" in CSV_COLUMNS
    assert "timestamp" in CSV_COLUMNS
    assert "tags" in CSV_COLUMNS


def test_scheduler_seconds_until_next_run_before_slot():
    bogota = ZoneInfo("America/Bogota")
    now = datetime(2026, 7, 14, 1, 0, 0, tzinfo=bogota)
    wait = seconds_until_next_run(now)
    assert 3500 < wait < 3700  # ~1 hour


def test_scheduler_seconds_until_next_run_after_slot():
    bogota = ZoneInfo("America/Bogota")
    now = datetime(2026, 7, 14, 3, 0, 0, tzinfo=bogota)
    wait = seconds_until_next_run(now)
    # Next day 02:00 → ~23 hours
    assert 22 * 3600 < wait < 24 * 3600
