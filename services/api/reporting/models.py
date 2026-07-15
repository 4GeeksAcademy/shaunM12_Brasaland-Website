"""Reporting schema: weekly location performance + pipeline run audit."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlmodel import Field, Session, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WeeklyLocationPerformance(SQLModel, table=True):
    __tablename__ = "weekly_location_performance"
    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "week_start",
            name="uq_weekly_location_performance_grain",
        ),
        {"schema": "reporting"},
    )

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True),
    )
    location_id: int = Field(index=True)
    country: str
    week_start: date = Field(index=True)
    total_purchase_cost: float = 0.0
    total_waste_cost: float = 0.0
    waste_ratio: float = 0.0
    stockout_events_count: int = 0
    price_alert_events_count: int = 0
    currency: str
    computed_at: datetime = Field(default_factory=_utc_now)


class PipelineRun(SQLModel, table=True):
    __tablename__ = "pipeline_runs"
    __table_args__ = ({"schema": "reporting"},)

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True),
    )
    flow_name: str
    week_start: Optional[date] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    start_time: datetime = Field(default_factory=_utc_now)
    end_time: Optional[datetime] = None
    records_extracted: int = 0
    records_loaded: int = 0
    records_processed: int = 0
    records_skipped_missing_cost: int = 0
    status: str = "running"
    errors: Optional[dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )


def ensure_reporting_schema(session: Session) -> None:
    """Create reporting schema + tables (migration path A — no Alembic)."""
    session.exec(text("CREATE SCHEMA IF NOT EXISTS reporting"))
    session.commit()
    bind = session.get_bind()
    SQLModel.metadata.create_all(
        bind,
        tables=[
            WeeklyLocationPerformance.__table__,
            PipelineRun.__table__,
        ],
    )
