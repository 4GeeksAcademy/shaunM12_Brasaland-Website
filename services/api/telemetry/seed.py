"""Reset and seed telemetry rows for local verification + reporting pipeline demos."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlmodel import Session

from database import get_engine

from .models import TelemetryEvent, ensure_telemetry_schema

# Locations 1–9 = CO/COP, 10–14 = US/USD (matches weekly_location_kpis).
_CO_LOCATIONS = list(range(1, 10))
_US_LOCATIONS = list(range(10, 15))
_ALL_LOCATIONS = _CO_LOCATIONS + _US_LOCATIONS

# Exactly one P6 fixture: waste without unit_cost (must not inflate waste cost).
_P6_MISSING_COST_LOCATION = 2


def _meta(location_id: int) -> tuple[str, str, float]:
    """Return country, currency, and a plausible unit_cost for the location."""
    if location_id <= 9:
        return "CO", "COP", 18000.0 + (location_id * 500.0)
    return "US", "USD", 10.0 + (location_id - 10) * 2.5


def _iso_week_monday(ts: datetime) -> datetime:
    d = ts.astimezone(timezone.utc).date()
    monday = d - timedelta(days=d.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)


def _seed_rows(now: datetime) -> list[TelemetryEvent]:
    """Dense KPI-complete fixture across locations 1–14 and both lookback weeks.

    Every purchase/waste has quantity + unit_cost except exactly one waste row
    at location 2 (P6). Sparse reporting therefore fills most grains.
    """
    now = now.astimezone(timezone.utc).replace(microsecond=0)
    this_monday = _iso_week_monday(now)
    prev_monday = this_monday - timedelta(weeks=1)

    rows: list[TelemetryEvent] = []
    inbound_id = 1000
    outbound_id = 2000

    def add(
        event_type: str,
        when: datetime,
        *,
        location_id: int,
        quantity: float | None = None,
        unit_cost: float | None = None,
        include_unit_cost: bool = True,
        extra: dict | None = None,
        level: str = "info",
        service: str = "api",
        value: float | None = None,
    ) -> None:
        nonlocal inbound_id, outbound_id
        country, currency, default_cost = _meta(location_id)
        tags: dict = {
            "location_id": location_id,
            "country": country,
            "currency": currency,
            "product_id": 7 if location_id % 2 else 8,
            "product_category": "meat",
            "unit": "kg",
            "created_by": "1",
        }
        if quantity is not None:
            tags["quantity"] = quantity
        if include_unit_cost and unit_cost is None and quantity is not None:
            unit_cost = default_cost
        if include_unit_cost and unit_cost is not None:
            tags["unit_cost"] = unit_cost
        if event_type == "inbound_order_created":
            inbound_id += 1
            tags["inbound_order_id"] = inbound_id
            tags["supplier_id"] = "12" if country == "CO" else "20"
        if event_type == "stock_waste_registered":
            outbound_id += 1
            tags["outbound_order_id"] = outbound_id
            tags["reason"] = "unspecified"
        if event_type == "stock_threshold_triggered":
            tags.pop("created_by", None)
            tags["current_stock"] = max(1, int((quantity or 5) // 2))
            tags["min_stock_threshold"] = 10
            tags["triggering_order_type"] = "OutboundOrder"
            tags["triggering_order_id"] = outbound_id
        if event_type == "ingredient_price_variance_detected":
            tags["supplier_id"] = "12" if country == "CO" else "20"
            tags["inbound_order_id"] = inbound_id
            tags["previous_unit_cost"] = (unit_cost or default_cost) * 0.9
            tags["new_unit_cost"] = unit_cost or default_cost
            tags["variance_pct"] = 10.0
            tags["threshold_pct"] = 10.0
            tags.pop("created_by", None)
            if "unit_cost" in tags:
                del tags["unit_cost"]
        if extra:
            tags.update(extra)
        rows.append(
            TelemetryEvent(
                event_type=event_type,
                timestamp=when,
                service=service,
                level=level,
                value=value if value is not None else quantity,
                tags=tags,
            )
        )

    # --- Current ISO week: every location gets purchase + costed waste ---
    for loc in _ALL_LOCATIONS:
        day_offset = (loc % 5) + 1  # Tue–Sat of current week when possible
        when_buy = this_monday + timedelta(days=min(day_offset, 6), hours=10)
        if when_buy > now:
            when_buy = now - timedelta(hours=loc)
        when_waste = when_buy + timedelta(hours=2)

        qty = 20.0 + loc
        add(
            "inbound_order_created",
            when_buy,
            location_id=loc,
            quantity=qty,
        )

        if loc == _P6_MISSING_COST_LOCATION:
            # Sole intentional skip for P6 (no unit_cost).
            add(
                "stock_waste_registered",
                when_waste,
                location_id=loc,
                quantity=3.0,
                include_unit_cost=False,
            )
        else:
            add(
                "stock_waste_registered",
                when_waste,
                location_id=loc,
                quantity=1.0 + (loc % 4),
            )

        if loc in {1, 3, 5, 8, 10, 12, 14}:
            add(
                "stock_threshold_triggered",
                when_waste + timedelta(hours=1),
                location_id=loc,
                quantity=5.0,
            )
        if loc in {3, 6, 10, 13}:
            add(
                "ingredient_price_variance_detected",
                when_buy + timedelta(hours=5),
                location_id=loc,
                quantity=15.0,
                unit_cost=_meta(loc)[2],
            )

    # --- Previous ISO week: full coverage so the week selector has a second page ---
    for loc in _ALL_LOCATIONS:
        when_buy = prev_monday + timedelta(days=(loc % 5) + 1, hours=11)
        when_waste = when_buy + timedelta(hours=3)
        add(
            "inbound_order_created",
            when_buy,
            location_id=loc,
            quantity=15.0 + loc,
        )
        # All previous-week waste is costed (the single P6 miss stays in current week).
        add(
            "stock_waste_registered",
            when_waste,
            location_id=loc,
            quantity=2.0 + (loc % 3),
        )
        if loc in {2, 7, 11}:
            add(
                "stock_threshold_triggered",
                when_waste + timedelta(hours=1),
                location_id=loc,
                quantity=4.0,
            )

    # A few non-KPI noise rows (must not create grains by themselves).
    rows.append(
        TelemetryEvent(
            event_type="outbound_order_failed",
            timestamp=now - timedelta(hours=3),
            service="api",
            level="info",
            value=8.0,
            tags={
                "error_code": "insufficient_stock",
                "product_id": 7,
                "location_id": 4,
                "country": "CO",
                "quantity_requested": 8,
            },
        )
    )
    rows.append(
        TelemetryEvent(
            event_type="user_login_failed",
            timestamp=now - timedelta(hours=1),
            service="api",
            level="info",
            value=None,
            tags={"failure_reason": "invalid_credentials", "location_id": 11},
        )
    )

    return rows


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
