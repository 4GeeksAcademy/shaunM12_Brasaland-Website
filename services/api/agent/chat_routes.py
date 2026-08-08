"""WebSocket routes for Support Agent chat streaming (Milestone 10 Part 2)."""

from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlmodel import Session

from auth.security import JWTError, decode_access_token
from database import get_engine
from users.repository import get_user_record

from .chat_models import ensure_agent_chat_schema
from .chat_orchestrator import get_agent_chat_orchestrator
from .chat_pubsub import (
    EVENT_INTERRUPT_REQUESTED,
    EVENT_SESSION_SYNC,
    EVENT_USER_MESSAGE,
    format_chat_frame,
    get_agent_chat_pubsub,
)
from .chat_repository import (
    build_session_sync_payload,
    create_session_on_connect,
    get_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent-chat"])

WS_CLOSE_POLICY = 4403
WS_CLOSE_UNAUTHORIZED = 4401


def _resolve_ws_user(access_token: str | None):
    if not access_token:
        return None
    try:
        payload = decode_access_token(access_token)
        if payload.get("type") is not None:
            return None
        subject = payload.get("sub")
        if subject is None:
            return None
        user_id = int(subject)
    except (JWTError, ValueError):
        return None

    user = get_user_record(user_id)
    if user is None or not user.is_active:
        return None
    return user


def _parse_uuid(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(UUID(value.strip()))
    except ValueError:
        return None


async def _send_session_sync(websocket: WebSocket, session_id: str) -> None:
    with Session(get_engine()) as db:
        ensure_agent_chat_schema(db)
        payload = build_session_sync_payload(db, session_id)
    await _send_chat_frame(websocket, format_chat_frame(EVENT_SESSION_SYNC, payload))


async def _send_chat_frame(websocket: WebSocket, frame: str) -> bool:
    """Send one WS text frame; return False when the client has disconnected."""
    try:
        await websocket.send_text(frame)
    except WebSocketDisconnect:
        return False
    return True


@router.websocket("/chat/ws")
async def agent_chat_websocket(websocket: WebSocket) -> None:
    """Bidirectional Support Agent chat channel."""
    session_id = _parse_uuid(websocket.query_params.get("session_id"))
    access_token = websocket.query_params.get("access_token")

    if session_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid session_id")
        return

    user = _resolve_ws_user(access_token)
    if user is None:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="Unauthorized")
        return

    with Session(get_engine()) as db:
        ensure_agent_chat_schema(db)
        existing = get_session(db, session_id)
        if existing is not None and existing.user_id != user.id:
            await websocket.close(code=WS_CLOSE_POLICY, reason="Forbidden")
            return
        create_session_on_connect(db, session_id=session_id, user_id=user.id)

    await websocket.accept()

    pubsub = get_agent_chat_pubsub()
    orchestrator = get_agent_chat_orchestrator()
    queue = await pubsub.subscribe(session_id)
    auth_header = f"Bearer {access_token}" if access_token else None

    await _send_session_sync(websocket, session_id)

    async def forward_pubsub() -> None:
        try:
            while True:
                frame = await queue.get()
                if not await _send_chat_frame(websocket, frame):
                    break
        except asyncio.CancelledError:
            raise

    forward_task = asyncio.create_task(forward_pubsub())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                if not await _send_chat_frame(
                    websocket,
                    format_chat_frame(
                        "error",
                        {
                            "session_id": session_id,
                            "code": "invalid_frame",
                            "message": "WebSocket frame must be JSON.",
                        },
                    ),
                ):
                    break
                continue

            event = payload.get("event")
            data = payload.get("data") or {}
            if not isinstance(data, dict):
                data = {}

            if event == EVENT_USER_MESSAGE:
                content = str(data.get("content") or "")
                asyncio.create_task(
                    orchestrator.handle_user_message(
                        session_id=session_id,
                        content=content,
                        user_id=user.id,
                        auth_header=auth_header,
                    )
                )
            elif event == EVENT_INTERRUPT_REQUESTED:
                new_input = str(data.get("new_input") or "")
                asyncio.create_task(
                    orchestrator.handle_interrupt(
                        session_id=session_id,
                        new_input=new_input,
                        user_id=user.id,
                        auth_header=auth_header,
                    )
                )
            else:
                if not await _send_chat_frame(
                    websocket,
                    format_chat_frame(
                        "error",
                        {
                            "session_id": session_id,
                            "code": "unknown_event",
                            "message": f"Unsupported event: {event!r}",
                        },
                    ),
                ):
                    break
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        try:
            await forward_task
        except (asyncio.CancelledError, WebSocketDisconnect):
            pass
        await pubsub.unsubscribe(session_id, queue)


__all__ = ["router"]
