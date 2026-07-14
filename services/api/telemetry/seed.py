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
            event_type="inbound_order_created",
            timestamp=now - timedelta(hours=5),
            service="api",
            level="info",
            value=50.0,
            tags={
                "inbound_order_id": 1,
                "product_id": 7,
                "product_category": "meat",
                "quantity": 50,
                "unit": "kg",
                "location_id": 3,
                "country": "CO",
                "supplier_id": "12",
                "currency": "COP",
                "unit_cost": 20.0,
                "created_by": "1",
            },
        ),
        TelemetryEvent(
            event_type="outbound_order_created",
            timestamp=now - timedelta(hours=3),
            service="api",
            level="info",
            value=12.0,
            tags={
                "outbound_order_id": 2,
                "product_id": 7,
                "product_category": "meat",
                "quantity": 12,
                "unit": "kg",
                "location_id": 11,
                "country": "US",
                "currency": "USD",
                "created_by": "1",
            },
        ),
        TelemetryEvent(
            event_type="stock_waste_registered",
            timestamp=now - timedelta(hours=2, minutes=30),
            service="api",
            level="info",
            value=3.0,
            tags={
                "outbound_order_id": 3,
                "product_id": 7,
                "product_category": "meat",
                "quantity": 3,
                "unit": "kg",
                "unit_cost": 20000.0,
                "reason": "unspecified",
                "location_id": 1,
                "country": "CO",
                "currency": "COP",
                "created_by": "1",
            },
        ),
        TelemetryEvent(
            event_type="outbound_order_failed",
            timestamp=now - timedelta(hours=2),
            service="api",
            level="info",
            value=8.0,
            tags={
                "error_code": "insufficient_stock",
                "product_id": 7,
                "location_id": 3,
                "country": "CO",
                "quantity_requested": 8,
            },
        ),
        TelemetryEvent(
            event_type="stock_threshold_triggered",
            timestamp=now - timedelta(hours=1, minutes=45),
            service="api",
            level="info",
            value=8.0,
            tags={
                "product_id": 7,
                "product_category": "meat",
                "location_id": 3,
                "country": "CO",
                "current_stock": 8,
                "min_stock_threshold": 10,
                "unit": "kg",
                "currency": "COP",
                "triggering_order_type": "OutboundOrder",
                "triggering_order_id": 2,
            },
        ),
        TelemetryEvent(
            event_type="ingredient_price_variance_detected",
            timestamp=now - timedelta(hours=1, minutes=15),
            service="api",
            level="info",
            value=50.0,
            tags={
                "inbound_order_id": 4,
                "product_id": 7,
                "product_category": "meat",
                "supplier_id": "12",
                "location_id": 3,
                "country": "CO",
                "quantity": 20,
                "unit": "kg",
                "currency": "COP",
                "previous_unit_cost": 20.0,
                "new_unit_cost": 24.0,
                "variance_pct": 20.0,
                "threshold_pct": 10.0,
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
                "product_count": 34,
                "view_source": "backoffice",
            },
        ),
        TelemetryEvent(
            event_type="user_login_failed",
            timestamp=now - timedelta(minutes=30),
            service="api",
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
