"""SQLModel tables for optional Postgres telemetry sinks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TelemetryEvent(SQLModel, table=True):
    """Standard telemetry events (stream + batch)."""

    __tablename__ = "telemetry_events"

    id: int | None = Field(default=None, primary_key=True)
    event_id: str = Field(index=True, unique=True)
    timestamp: datetime
    session_id: str
    user_id: str
    event_type: str = Field(index=True)
    schema_version: int
    request_id: str = Field(index=True)
    processing: str
    properties: dict[str, Any] = Field(sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_utc_now)


class TelemetryEventRestricted(SQLModel, table=True):
    """Restricted telemetry (e.g. theft consumption) — separate access boundary."""

    __tablename__ = "telemetry_events_restricted"

    id: int | None = Field(default=None, primary_key=True)
    event_id: str = Field(index=True, unique=True)
    timestamp: datetime
    session_id: str
    user_id: str
    event_type: str = Field(index=True)
    schema_version: int
    request_id: str = Field(index=True)
    processing: str
    properties: dict[str, Any] = Field(sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_utc_now)
