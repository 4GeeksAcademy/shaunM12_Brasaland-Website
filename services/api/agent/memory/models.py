"""SQLModel tables for Support Agent memory (context-26 P26-L13)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, Index, inspect, text
from sqlalchemy.types import JSON
from sqlmodel import Field, Session, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentMemoryEntry(SQLModel, table=True):
    """Approved operational memory fact (upserted per P26-L3c)."""

    __tablename__ = "agent_memory_entries"
    __table_args__ = (
        Index("ix_agent_memory_entries_location_category", "location_id", "category"),
        Index("ix_agent_memory_entries_user_category", "user_id", "category"),
    )

    id: int | None = Field(default=None, primary_key=True)
    location_id: int | None = Field(default=None, index=True)
    user_id: int | None = Field(default=None, index=True)
    category: str = Field(index=True, max_length=64)
    key: str = Field(max_length=128)
    value: str
    source: str = Field(default="user_confirmed", max_length=64)
    approved_by: int = Field(index=True)
    approved_at: datetime = Field(default_factory=_utc_now, index=True)
    expires_at: datetime | None = Field(default=None, index=True)


class AgentMemoryAuditLog(SQLModel, table=True):
    """Append-only proposal/decision audit trail (P26-L1a)."""

    __tablename__ = "agent_memory_audit_log"
    __table_args__ = (Index("ix_agent_memory_audit_user_created", "user_id", "created_at"),)

    id: int | None = Field(default=None, primary_key=True)
    thread_id: str | None = Field(default=None, max_length=64)
    user_id: int = Field(index=True)
    proposal_json: dict[str, Any] = Field(sa_column=Column(JSON))
    outcome: str = Field(index=True, max_length=64)
    reason: str | None = Field(default=None, max_length=128)
    user_message: str | None = None
    superseded_value: str | None = None
    created_at: datetime = Field(default_factory=_utc_now, index=True)


def _postgres_partial_indexes(session: Session) -> None:
    dialect = session.get_bind().dialect.name
    if dialect != "postgresql":
        return
    session.exec(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_memory_global
            ON agent_memory_entries (location_id, category, key)
            WHERE user_id IS NULL AND category <> 'preferences'
            """
        )
    )
    session.exec(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_memory_preferences
            ON agent_memory_entries (user_id, category, key)
            WHERE category = 'preferences'
            """
        )
    )
    session.commit()


def ensure_agent_memory_schema(session: Session) -> None:
    """Create memory tables if missing (telemetry-style bootstrap, P26-L13a)."""
    bind = session.get_bind()
    inspector = inspect(bind)
    tables = {AgentMemoryEntry.__tablename__, AgentMemoryAuditLog.__tablename__}
    missing = [name for name in tables if not inspector.has_table(name)]
    if missing:
        SQLModel.metadata.create_all(
            bind,
            tables=[AgentMemoryEntry.__table__, AgentMemoryAuditLog.__table__],
        )
    _postgres_partial_indexes(session)


__all__ = ["AgentMemoryAuditLog", "AgentMemoryEntry", "ensure_agent_memory_schema"]
