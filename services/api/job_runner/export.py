"""Export one UTC day of ``telemetry_events`` to ``data/raw/telemetry_YYYY-MM-DD.csv``."""

from __future__ import annotations

import csv
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlmodel import Session

logger = logging.getLogger("job_runner.export")

CSV_COLUMNS = (
    "id",
    "event_type",
    "timestamp",
    "service",
    "level",
    "value",
    "tags",
    "created_at",
)


def telemetry_csv_path(raw_dir: Path, target_date: date) -> Path:
    return raw_dir / f"telemetry_{target_date.isoformat()}.csv"


def utc_day_bounds(target_date: date) -> tuple[datetime, datetime]:
    start = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        tzinfo=timezone.utc,
    )
    end = start + timedelta(days=1)
    return start, end


def export_telemetry_day_csv(
    session: Session,
    *,
    target_date: date,
    raw_dir: Path,
) -> tuple[Path, int, bool]:
    """Write CSV for ``target_date`` if missing.

    Returns ``(path, row_count, wrote_file)``. When the file already exists,
    ``wrote_file`` is False and the file is not rewritten.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = telemetry_csv_path(raw_dir, target_date)
    if path.exists():
        logger.info(
            "%s job_name=nightly_export status=processing "
            "csv already exists path=%s (skip rewrite)",
            datetime.now(timezone.utc).isoformat(),
            path,
        )
        return path, 0, False

    start, end = utc_day_bounds(target_date)
    rows = session.execute(
        text(
            """
            SELECT id, event_type, timestamp, service, level, value, tags, created_at
            FROM telemetry_events
            WHERE timestamp >= :period_start
              AND timestamp < :period_end
            ORDER BY timestamp ASC, id ASC
            """
        ),
        {"period_start": start, "period_end": end},
    ).mappings().all()

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(_serialize_row(dict(row)))

    logger.info(
        "%s job_name=nightly_export status=processing "
        "exported rows=%s path=%s",
        datetime.now(timezone.utc).isoformat(),
        len(rows),
        path,
    )
    return path, len(rows), True


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in CSV_COLUMNS:
        value = row.get(key)
        if isinstance(value, datetime):
            out[key] = value.isoformat()
        elif isinstance(value, (dict, list)):
            out[key] = json.dumps(value, default=str)
        elif value is None:
            out[key] = ""
        else:
            out[key] = value
    return out
