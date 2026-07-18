"""SQLModel table for Celery dead-letter records (``task_dead_letters``)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Session, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskDeadLetter(SQLModel, table=True):
    __tablename__ = "task_dead_letters"
    __table_args__ = (
        UniqueConstraint("task_id", name="uq_task_dead_letters_task_id"),
    )

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True),
    )
    task_id: str = Field(index=True, max_length=255)
    attempt: int
    error_message: str
    task_name: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=_utc_now)


def ensure_task_dead_letters_schema(session: Session) -> None:
    """Create ``task_dead_letters`` table if missing."""
    bind = session.get_bind()
    SQLModel.metadata.create_all(bind, tables=[TaskDeadLetter.__table__])
