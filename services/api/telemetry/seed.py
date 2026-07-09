"""Reset and seed telemetry rows for local verification."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlmodel import Session

from database import get_engine

from .models import TelemetryEvent, ensure_telemetry_schema


def _seed_rows(now: datetime) -> list[TelemetryEvent]:
    return [
        TelemetryEvent(
            event_type="supply_order_created",
            timestamp=now - timedelta(hours=5),
            service="backoffice",
            level="info",
            value=50.0,
            tags={
                "ingredient_id": 7,
                "quantity": 50,
                "location_id": 3,
                "supplier_id": "12",
            },
        ),
        TelemetryEvent(
            event_type="consumption_order_created",
            timestamp=now - timedelta(hours=3),
            service="backoffice",
            level="info",
            value=12.0,
            tags={
                "ingredient_id": 7,
                "quantity": 12,
                "reason": "consumption",
                "location_id": 11,
            },
        ),
        TelemetryEvent(
            event_type="consumption_order_failed",
            timestamp=now - timedelta(hours=2),
            service="backoffice",
            level="info",
            value=8.0,
            tags={
                "error_code": "insufficient_stock",
                "ingredient_id": 7,
                "location_id": 3,
                "quantity_requested": 8,
            },
        ),
        TelemetryEvent(
            event_type="ingredient_list_viewed",
            timestamp=now - timedelta(hours=1),
            service="backoffice",
            level="info",
            value=None,
            tags={
                "location_id": 3,
                "ingredient_count": 34,
                "view_source": "backoffice",
            },
        ),
        TelemetryEvent(
            event_type="user_login_failed",
            timestamp=now - timedelta(minutes=30),
            service="backoffice",
            level="info",
            value=None,
            tags={"failure_reason": "invalid_credentials", "location_id": 11},
        ),
    ]


def reset_and_seed_telemetry() -> int:
    """Purge telemetry rows and insert fresh mock data."""
    engine = get_engine()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with Session(engine) as session:
        ensure_telemetry_schema(session)
        session.exec(text("TRUNCATE telemetry_events RESTART IDENTITY CASCADE"))
        rows = _seed_rows(now)
        for row in rows:
            session.add(row)
        session.commit()
        return len(rows)


def main() -> int:
    try:
        inserted = reset_and_seed_telemetry()
    except Exception as exc:  # pragma: no cover - CLI message path
        print(f"Telemetry reseed failed: {exc}", file=sys.stderr)
        return 1

    print(f"Telemetry reset complete: inserted {inserted} row(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

