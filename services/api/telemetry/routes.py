"""Telemetry ingestion endpoints."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import insert
from sqlmodel import Session

import config
from database import get_db
from .analysis import auth_failure_rate_per_day
from .analysis import daily_consumption_by_product_and_location
from .analysis import stock_out_frequency
from .analysis import waste_loss_ratio
from .constants import event_definition
from .emit import enrich_properties
from .models import TelemetryEvent as TelemetryEventRow, ensure_telemetry_schema

logger = logging.getLogger("brasaland.telemetry.stub")
_REPORT_CACHE_TTL_SECONDS = 60
_REPORT_CACHE: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}


class TelemetryEvent(BaseModel):
    """Standard telemetry envelope accepted by the ingestion endpoint."""

    eventId: str
    timestamp: datetime
    sessionId: str
    userId: str
    event_type: str
    schemaVersion: int
    requestId: str
    service: str
    properties: dict[str, Any] = Field(default_factory=dict)


class TelemetryBatch(BaseModel):
    """Batch wrapper for telemetry ingestion."""

    events: list[TelemetryEvent] = Field(default_factory=list)


router = APIRouter(tags=["telemetry"])


def _get_optional_db() -> Any:
    if not config.DATABASE_URL:
        yield None
        return
    yield from get_db()


def _project_numeric_value(properties: dict[str, Any]) -> float | None:
    raw = properties.get("quantity")
    if raw is None:
        raw = properties.get("quantity_requested")
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


def _validate_allowlist(event_type: str, properties: dict[str, Any]) -> None:
    definition = event_definition(event_type)
    allowlist = set(definition.get("propertyAllowlist", []))
    extra = set(properties) - allowlist
    if extra:
        raise ValueError(f"rejects unknown properties: {sorted(extra)}")


def _parse_report_datetime(raw: str, *, label: str) -> datetime:
    candidate = raw.strip()
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{label} must be a valid ISO 8601 datetime",
        ) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _resolve_report_period(
    start_date: str | None,
    end_date: str | None,
) -> tuple[datetime, datetime]:
    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    resolved_end = _parse_report_datetime(end_date, label="end_date") if end_date else now_utc
    resolved_start = (
        _parse_report_datetime(start_date, label="start_date")
        if start_date
        else resolved_end - timedelta(days=7)
    )
    if resolved_start >= resolved_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date must be earlier than end_date",
        )
    return resolved_start, resolved_end


def _build_report(
    *,
    start: datetime,
    end: datetime,
    session: Session | None,
) -> dict[str, Any]:
    return {
        "period": {
            "from": start.date().isoformat(),
            "to": end.date().isoformat(),
        },
        "metrics": {
            "daily_consumption_by_product_and_location": daily_consumption_by_product_and_location(
                start,
                end,
                session=session,
            ),
            "stock_out_frequency": stock_out_frequency(
                start,
                end,
                session=session,
            ),
            "waste_loss_ratio": waste_loss_ratio(
                start,
                end,
                session=session,
            ),
            "auth_failure_rate_per_day": auth_failure_rate_per_day(
                start,
                end,
                session=session,
            ),
        },
    }


def _ingest_stub(payload: dict[str, Any]) -> dict[str, int]:
    """Phase 2: envelope verification only, no persistence."""
    try:
        batch = TelemetryBatch.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(),
        ) from exc
    count = len(batch.events)
    event_types = [event.event_type for event in batch.events]
    logger.info("telemetry events received=%d event_types=%s", count, event_types)
    return {"received": count}


def _ingest_storage(
    payload: dict[str, Any],
    session: Session | None,
) -> dict[str, int]:
    """Phase 3: per-event validation + mixed-batch persistence."""
    raw_events = payload.get("events", [])
    if not isinstance(raw_events, list):
        return {"received": 0, "stored": 0, "rejected": 0}

    received = len(raw_events)
    rejected = 0
    valid_rows: list[dict[str, Any]] = []
    event_types: list[str] = []
    for raw_event in raw_events:
        try:
            event = TelemetryEvent.model_validate(raw_event)
            _validate_allowlist(event.event_type, event.properties)
        except Exception:
            rejected += 1
            continue

        event_types.append(event.event_type)
        tags = enrich_properties(dict(event.properties))
        valid_rows.append(
            {
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "service": event.service,
                "level": "info",
                "value": _project_numeric_value(tags),
                "tags": tags,
            }
        )

    stored = 0
    if valid_rows and session is not None:
        ensure_telemetry_schema(session)
        # One bulk insert operation per batch for Phase 3 throughput/atomicity.
        session.execute(insert(TelemetryEventRow), valid_rows)
        session.commit()
        stored = len(valid_rows)

    logger.info(
        "telemetry events received=%d stored=%d rejected=%d event_types=%s",
        received,
        stored,
        rejected,
        event_types,
    )
    return {"received": received, "stored": stored, "rejected": rejected}


@router.post("/events")
def ingest_events(
    payload: dict[str, Any] = Body(default_factory=dict),
    session: Session | None = Depends(_get_optional_db),
) -> dict[str, int]:
    """Ingress endpoint that supports phase-switched behavior."""
    # Read from config now to establish endpoint contract from day one.
    _expected_path = config.TELEMETRY_ENDPOINT
    mode = config.TELEMETRY_PHASE_MODE
    if mode == "storage":
        return _ingest_storage(payload, session)
    return _ingest_stub(payload)


@router.get("/report")
def get_telemetry_report(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    session: Session | None = Depends(_get_optional_db),
) -> dict[str, Any]:
    """Phase 4 aggregated telemetry metrics for a report period."""
    period_start, period_end = _resolve_report_period(start_date, end_date)
    cache_key = (period_start.isoformat(), period_end.isoformat())
    cached = _REPORT_CACHE.get(cache_key)
    now_monotonic = time.monotonic()
    if cached and now_monotonic - cached[0] < _REPORT_CACHE_TTL_SECONDS:
        return cached[1]

    report = _build_report(start=period_start, end=period_end, session=session)
    _REPORT_CACHE[cache_key] = (now_monotonic, report)
    return report

