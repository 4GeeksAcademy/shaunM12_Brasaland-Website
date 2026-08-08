"""Repository helpers for agent chat sessions and messages."""

from __future__ import annotations

from datetime import timezone
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import Session, select

from .chat_models import (
    AGENT_ID_MANAGER_SUPPORT,
    AgentChatMessage,
    AgentChatSession,
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_USER,
    MESSAGE_STATUS_COMPLETE,
    MESSAGE_STATUS_INTERRUPTED,
    MESSAGE_STATUS_STREAMING,
    SESSION_STATUS_ACTIVE,
    ensure_agent_chat_schema,
)


def _iso_utc(value) -> str:
    created_at = value
    if created_at.tzinfo is not None:
        created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)
    return f"{created_at.isoformat()}Z"


def message_to_sync_item(message: AgentChatMessage) -> dict[str, Any]:
    """Build one ``session_sync.messages[]`` element."""
    return {
        "message_id": message.message_id,
        "role": message.role,
        "content": message.content,
        "status": message.status,
        "created_at": _iso_utc(message.created_at),
    }


def new_message_id() -> str:
    """Mint a server-side UUID v4 string for ``message_id`` (M10-P2-E8)."""
    return str(uuid4())


def _validate_message_id(message_id: str) -> str:
    return str(UUID(message_id))


def get_session(session: Session, session_id: str) -> AgentChatSession | None:
    ensure_agent_chat_schema(session)
    return session.get(AgentChatSession, session_id)


def create_session_on_connect(
    session: Session,
    *,
    session_id: str,
    user_id: int,
    agent_id: str = AGENT_ID_MANAGER_SUPPORT,
    location_id: int | None = None,
) -> AgentChatSession:
    """Create the session row on first successful WS connect; no-op if it exists."""
    ensure_agent_chat_schema(session)
    existing = session.get(AgentChatSession, session_id)
    if existing is not None:
        return existing
    row = AgentChatSession(
        session_id=session_id,
        agent_id=agent_id,
        user_id=user_id,
        location_id=location_id,
        status=SESSION_STATUS_ACTIVE,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_or_create_session(
    session: Session,
    *,
    session_id: str,
    user_id: int,
    agent_id: str = AGENT_ID_MANAGER_SUPPORT,
    location_id: int | None = None,
) -> AgentChatSession:
    """Backward-compatible alias for ``create_session_on_connect``."""
    return create_session_on_connect(
        session,
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        location_id=location_id,
    )


def list_messages(session: Session, session_id: str) -> list[AgentChatMessage]:
    ensure_agent_chat_schema(session)
    statement = (
        select(AgentChatMessage)
        .where(AgentChatMessage.session_id == session_id)
        .order_by(AgentChatMessage.created_at, AgentChatMessage.message_id)
    )
    return list(session.exec(statement).all())


def build_session_sync_payload(session: Session, session_id: str) -> dict[str, Any]:
    messages = list_messages(session, session_id)
    return {
        "session_id": session_id,
        "messages": [message_to_sync_item(row) for row in messages],
    }


def create_user_message(
    session: Session,
    *,
    session_id: str,
    content: str,
    message_id: str | None = None,
) -> AgentChatMessage:
    ensure_agent_chat_schema(session)
    resolved_message_id = _validate_message_id(message_id) if message_id else new_message_id()
    row = AgentChatMessage(
        message_id=resolved_message_id,
        session_id=session_id,
        role=MESSAGE_ROLE_USER,
        content=content.strip(),
        status=MESSAGE_STATUS_COMPLETE,
        sequence=0,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_assistant_message_streaming(
    session: Session,
    *,
    session_id: str,
    message_id: str | None = None,
) -> AgentChatMessage:
    ensure_agent_chat_schema(session)
    resolved_message_id = _validate_message_id(message_id) if message_id else new_message_id()
    row = AgentChatMessage(
        message_id=resolved_message_id,
        session_id=session_id,
        role=MESSAGE_ROLE_ASSISTANT,
        content="",
        status=MESSAGE_STATUS_STREAMING,
        sequence=0,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def append_assistant_token(
    session: Session,
    *,
    message_id: str,
    token: str,
    sequence: int,
) -> AgentChatMessage:
    ensure_agent_chat_schema(session)
    row = session.get(AgentChatMessage, message_id)
    if row is None:
        raise ValueError(f"Unknown assistant message_id={message_id!r}")
    row.content = f"{row.content}{token}"
    row.sequence = sequence
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def finalize_assistant_message(
    session: Session,
    *,
    message_id: str,
    status: str,
) -> AgentChatMessage:
    ensure_agent_chat_schema(session)
    row = session.get(AgentChatMessage, message_id)
    if row is None:
        raise ValueError(f"Unknown assistant message_id={message_id!r}")
    row.status = status
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_message(session: Session, message_id: str) -> AgentChatMessage | None:
    ensure_agent_chat_schema(session)
    return session.get(AgentChatMessage, message_id)


__all__ = [
    "append_assistant_token",
    "build_session_sync_payload",
    "create_assistant_message_streaming",
    "create_session_on_connect",
    "create_user_message",
    "finalize_assistant_message",
    "get_message",
    "get_or_create_session",
    "get_session",
    "list_messages",
    "message_to_sync_item",
    "new_message_id",
]
