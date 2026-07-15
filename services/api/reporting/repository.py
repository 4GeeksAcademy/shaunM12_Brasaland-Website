"""Read/write helpers for reporting tables."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, select

from .models import PipelineRun, WeeklyLocationPerformance, ensure_reporting_schema


def upsert_weekly_rows(session: Session, rows: list[dict[str, Any]]) -> int:
    """Upsert sparse KPI grains on (location_id, week_start). Returns load count."""
    ensure_reporting_schema(session)
    if not rows:
        return 0

    now = datetime.now(timezone.utc)
    statement = text(
        """
        INSERT INTO reporting.weekly_location_performance (
            id, location_id, country, week_start,
            total_purchase_cost, total_waste_cost, waste_ratio,
            stockout_events_count, price_alert_events_count,
            currency, computed_at
        ) VALUES (
            :id, :location_id, :country, :week_start,
            :total_purchase_cost, :total_waste_cost, :waste_ratio,
            :stockout_events_count, :price_alert_events_count,
            :currency, :computed_at
        )
        ON CONFLICT (location_id, week_start) DO UPDATE SET
            country = EXCLUDED.country,
            total_purchase_cost = EXCLUDED.total_purchase_cost,
            total_waste_cost = EXCLUDED.total_waste_cost,
            waste_ratio = EXCLUDED.waste_ratio,
            stockout_events_count = EXCLUDED.stockout_events_count,
            price_alert_events_count = EXCLUDED.price_alert_events_count,
            currency = EXCLUDED.currency,
            computed_at = EXCLUDED.computed_at
        """
    )
    for row in rows:
        session.execute(
            statement,
            {
                "id": str(uuid.uuid4()),
                "location_id": int(row["location_id"]),
                "country": str(row["country"]),
                "week_start": row["week_start"],
                "total_purchase_cost": float(row.get("total_purchase_cost") or 0),
                "total_waste_cost": float(row.get("total_waste_cost") or 0),
                "waste_ratio": float(row.get("waste_ratio") or 0),
                "stockout_events_count": int(row.get("stockout_events_count") or 0),
                "price_alert_events_count": int(
                    row.get("price_alert_events_count") or 0
                ),
                "currency": str(row["currency"]),
                "computed_at": now,
            },
        )
    session.commit()
    return len(rows)


def start_pipeline_run(
    session: Session,
    *,
    flow_name: str,
    week_start: date | None,
    period_start: datetime | None,
    period_end: datetime | None,
) -> uuid.UUID:
    ensure_reporting_schema(session)
    run = PipelineRun(
        flow_name=flow_name,
        week_start=week_start,
        period_start=period_start,
        period_end=period_end,
        status="running",
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    assert run.id is not None
    return run.id


def finish_pipeline_run(
    session: Session,
    run_id: uuid.UUID,
    *,
    status: str,
    records_extracted: int = 0,
    records_loaded: int = 0,
    records_skipped_missing_cost: int = 0,
    errors: dict[str, Any] | None = None,
) -> None:
    run = session.get(PipelineRun, run_id)
    if run is None:
        return
    run.status = status
    run.end_time = datetime.now(timezone.utc)
    run.records_extracted = records_extracted
    run.records_loaded = records_loaded
    run.records_processed = records_loaded
    run.records_skipped_missing_cost = records_skipped_missing_cost
    run.errors = errors
    session.add(run)
    session.commit()


def list_weekly_performance(
    session: Session,
    *,
    week_start: date | None = None,
) -> list[WeeklyLocationPerformance]:
    ensure_reporting_schema(session)
    if week_start is None:
        latest = session.exec(
            select(WeeklyLocationPerformance.week_start)
            .order_by(WeeklyLocationPerformance.week_start.desc())  # type: ignore[attr-defined]
            .limit(1)
        ).first()
        if latest is None:
            return []
        week_start = latest

    rows = session.exec(
        select(WeeklyLocationPerformance)
        .where(WeeklyLocationPerformance.week_start == week_start)
        .order_by(WeeklyLocationPerformance.location_id)
    ).all()
    return list(rows)


def latest_pipeline_run(session: Session) -> PipelineRun | None:
    ensure_reporting_schema(session)
    return session.exec(
        select(PipelineRun).order_by(PipelineRun.start_time.desc())  # type: ignore[attr-defined]
    ).first()
