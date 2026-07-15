"""SQLModel table for nightly orchestration audit (``reporting.job_runs``)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Optional

from sqlalchemy import Column, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Session, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


JOB_NAME_NIGHTLY_EXPORT = "nightly_export"

STALE_PROCESSING_HOURS_DEFAULT = 2


class JobRunStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobRun(SQLModel, table=True):
    __tablename__ = "job_runs"
    __table_args__ = (
        UniqueConstraint(
            "job_name",
            "target_date",
            name="uq_job_runs_job_name_target_date",
        ),
        {"schema": "reporting"},
    )

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True),
    )
    job_name: str = Field(index=True)
    target_date: date = Field(index=True)
    status: str = Field(default=JobRunStatus.PENDING.value, index=True)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)


def ensure_job_runs_schema(session: Session) -> None:
    """Create ``reporting`` schema + ``job_runs`` table if missing."""
    session.exec(text("CREATE SCHEMA IF NOT EXISTS reporting"))
    session.commit()
    bind = session.get_bind()
    SQLModel.metadata.create_all(bind, tables=[JobRun.__table__])
