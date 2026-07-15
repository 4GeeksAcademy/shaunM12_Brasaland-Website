"""SQLModel tables for telemetry persistence (Phase 3 contract)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, Index, inspect, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, Session


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TelemetryEvent(SQLModel, table=True):
    """Append-only telemetry event row in Supabase/Postgres."""

    __tablename__ = "telemetry_events"
    __table_args__ = (
        Index("ix_telemetry_events_tags_gin", "tags", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_type: str = Field(index=True)
    timestamp: datetime = Field(index=True)
    service: str
    level: str = Field(default="info")
    value: float | None = None
    tags: dict[str, Any] = Field(sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_utc_now)


def ensure_telemetry_schema(session: Session) -> None:
    """Ensure telemetry table matches the Phase 3 column contract.

    This migration is intentionally destructive for legacy telemetry tables:
    when an old envelope-shaped table is detected, telemetry rows are dropped
    so the new contract can be recreated cleanly.
    """

    bind = session.get_bind()
    inspector = inspect(bind)
    has_table = inspector.has_table("telemetry_events")
    if not has_table:
        SQLModel.metadata.create_all(bind)
        return

    columns = {col["name"] for col in inspector.get_columns("telemetry_events")}
    required = {
        "id",
        "event_type",
        "timestamp",
        "service",
        "level",
        "value",
        "tags",
        "created_at",
    }
    if required.issubset(columns):
        return

    # Legacy shape detected: drop old telemetry tables and recreate with
    # the Phase 3 tags-based contract. This intentionally removes old rows.
    session.exec(text("DROP TABLE IF EXISTS telemetry_events_restricted CASCADE"))
    session.exec(text("DROP TABLE IF EXISTS telemetry_events CASCADE"))
    session.commit()
    SQLModel.metadata.create_all(bind)
