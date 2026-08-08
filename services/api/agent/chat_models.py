"""Postgres chat transcript tables for Milestone 10 Part 2 WebSocket streaming."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Index, inspect
from sqlmodel import Field, Session, SQLModel

AGENT_ID_MANAGER_SUPPORT = "manager_support"

SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_INTERRUPTED = "interrupted"
SESSION_STATUS_CLOSED = "closed"

MESSAGE_STATUS_COMPLETE = "complete"
MESSAGE_STATUS_INTERRUPTED = "interrupted"
MESSAGE_STATUS_STREAMING = "streaming"

MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentChatSession(SQLModel, table=True):
    """One support chat conversation bound to a LangGraph thread_id."""

    __tablename__ = "agent_chat_sessions"

    session_id: str = Field(primary_key=True, max_length=36)
    agent_id: str = Field(default=AGENT_ID_MANAGER_SUPPORT, max_length=64, index=True)
    user_id: int = Field(index=True)
    location_id: int | None = Field(default=None, index=True)
    status: str = Field(default=SESSION_STATUS_ACTIVE, max_length=32, index=True)
    created_at: datetime = Field(default_factory=_utc_now, index=True)


class AgentChatMessage(SQLModel, table=True):
    """Persisted chat message for UI transcript and session_sync."""

    __tablename__ = "agent_chat_messages"
    __table_args__ = (
        Index("ix_agent_chat_messages_session_created", "session_id", "created_at"),
    )

    message_id: str = Field(primary_key=True, max_length=36)
    session_id: str = Field(foreign_key="agent_chat_sessions.session_id", index=True, max_length=36)
    role: str = Field(max_length=16, index=True)
    content: str = Field(default="")
    status: str = Field(default=MESSAGE_STATUS_COMPLETE, max_length=16, index=True)
    sequence: int = Field(default=0)
    created_at: datetime = Field(default_factory=_utc_now, index=True)


def ensure_agent_chat_schema(session: Session) -> None:
    """Create chat tables when missing (repo bootstrap convention)."""
    bind = session.get_bind()
    inspector = inspect(bind)
    tables = {AgentChatSession.__tablename__, AgentChatMessage.__tablename__}
    missing = [name for name in tables if not inspector.has_table(name)]
    if missing:
        SQLModel.metadata.create_all(
            bind,
            tables=[AgentChatSession.__table__, AgentChatMessage.__table__],
        )


__all__ = [
    "AGENT_ID_MANAGER_SUPPORT",
    "AgentChatMessage",
    "AgentChatSession",
    "MESSAGE_ROLE_ASSISTANT",
    "MESSAGE_ROLE_USER",
    "MESSAGE_STATUS_COMPLETE",
    "MESSAGE_STATUS_INTERRUPTED",
    "MESSAGE_STATUS_STREAMING",
    "SESSION_STATUS_ACTIVE",
    "SESSION_STATUS_CLOSED",
    "SESSION_STATUS_INTERRUPTED",
    "ensure_agent_chat_schema",
]
