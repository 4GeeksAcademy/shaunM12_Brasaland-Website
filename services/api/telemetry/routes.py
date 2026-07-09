"""Telemetry ingestion endpoints."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import insert
from sqlmodel import Session

import config
from database import get_db
from .constants import event_definition
from .models import TelemetryEvent as TelemetryEventRow, ensure_telemetry_schema

logger = logging.getLogger("brasaland.telemetry.stub")


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
        valid_rows.append(
            {
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "service": event.service,
                "level": "info",
                "value": _project_numeric_value(event.properties),
                "tags": event.properties,
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

