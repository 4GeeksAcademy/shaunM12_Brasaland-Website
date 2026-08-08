"""Session turn orchestrator for Support Agent WebSocket chat."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from database import get_engine
from sqlmodel import Session

from .chat_models import MESSAGE_STATUS_COMPLETE, MESSAGE_STATUS_INTERRUPTED
from .chat_pubsub import (
    EVENT_ERROR,
    EVENT_GENERATION_COMPLETED,
    EVENT_GENERATION_INTERRUPTED,
    EVENT_SESSION_SYNC,
    EVENT_TOKEN_CHUNK,
    publish_chat_event,
)
from .chat_repository import (
    append_assistant_token,
    build_session_sync_payload,
    create_assistant_message_streaming,
    create_user_message,
    finalize_assistant_message,
)
from .generation import chunk_text_for_streaming, iter_llm_completion_tokens

logger = logging.getLogger(__name__)

ERROR_TURN_IN_PROGRESS = "turn_in_progress"


@dataclass
class _SessionTurnState:
    turn_in_progress: bool = False
    streaming: bool = False
    current_message_id: str | None = None
    stream_task: asyncio.Task[None] | None = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)


class AgentChatOrchestrator:
    """One orchestrator per ``session_id`` — runs graph + streaming, publishes events."""

    def __init__(self) -> None:
        self._sessions: dict[str, _SessionTurnState] = {}
        self._lock = asyncio.Lock()

    def _session_state(self, session_id: str) -> _SessionTurnState:
        return self._sessions.setdefault(session_id, _SessionTurnState())

    async def handle_user_message(
        self,
        *,
        session_id: str,
        content: str,
        user_id: int,
        auth_header: str | None,
    ) -> None:
        text = content.strip()
        if not text:
            self._publish_error(session_id, code="invalid_message", message="content must not be empty")
            return

        async with self._lock:
            state = self._session_state(session_id)
            if state.turn_in_progress:
                if state.streaming:
                    self._publish_error(
                        session_id,
                        code="streaming",
                        message="Submit interrupt_requested while the assistant is streaming.",
                    )
                else:
                    self._publish_error(
                        session_id,
                        code=ERROR_TURN_IN_PROGRESS,
                        message="A turn is already in progress for this session.",
                    )
                return
            state.turn_in_progress = True

        with Session(get_engine()) as db:
            create_user_message(db, session_id=session_id, content=text)

        self._publish_session_sync(session_id)

        await self._run_turn(
            session_id=session_id,
            question=text,
            user_id=user_id,
            auth_header=auth_header,
        )

    async def handle_interrupt(
        self,
        *,
        session_id: str,
        new_input: str,
        user_id: int,
        auth_header: str | None,
    ) -> None:
        text = new_input.strip()
        if not text:
            self._publish_error(session_id, code="invalid_message", message="new_input must not be empty")
            return

        state = self._session_state(session_id)
        if not state.streaming or state.stream_task is None or not state.current_message_id:
            self._publish_error(
                session_id,
                code="not_streaming",
                message="No assistant response is currently streaming.",
            )
            return

        interrupted_message_id = state.current_message_id
        await self._cancel_active_stream(session_id)

        with Session(get_engine()) as db:
            finalize_assistant_message(
                db,
                message_id=interrupted_message_id,
                status=MESSAGE_STATUS_INTERRUPTED,
            )
            create_user_message(db, session_id=session_id, content=text)

        publish_chat_event(
            session_id,
            EVENT_GENERATION_INTERRUPTED,
            {"session_id": session_id, "message_id": interrupted_message_id},
        )
        self._publish_session_sync(session_id)

        await self._run_turn(
            session_id=session_id,
            question=text,
            user_id=user_id,
            auth_header=auth_header,
        )

    async def _cancel_active_stream(self, session_id: str) -> None:
        state = self._session_state(session_id)
        state.cancel_event.set()
        task = state.stream_task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        state.stream_task = None
        state.streaming = False
        # Leave cancel_event set so an in-flight ``_run_turn`` exits before finalize.

    async def _run_turn(
        self,
        *,
        session_id: str,
        question: str,
        user_id: int,
        auth_header: str | None,
    ) -> None:
        state = self._session_state(session_id)
        if not state.turn_in_progress:
            state.turn_in_progress = True
        state.cancel_event = asyncio.Event()

        with Session(get_engine()) as db:
            assistant = create_assistant_message_streaming(db, session_id=session_id)
        message_id = assistant.message_id
        state.current_message_id = message_id

        publish_chat_event(
            session_id,
            EVENT_TOKEN_CHUNK,
            {
                "session_id": session_id,
                "message_id": message_id,
                "token": "",
                "sequence": 0,
            },
        )

        try:
            graph_state = await asyncio.to_thread(
                self._invoke_graph,
                question=question,
                session_id=session_id,
                user_id=user_id,
                auth_header=auth_header,
            )
            answer = (graph_state.get("answer") or "").strip()
            state.streaming = True
            if answer:
                state.stream_task = asyncio.create_task(
                    self._stream_answer_text(
                        session_id=session_id,
                        message_id=message_id,
                        answer=answer,
                        cancel_event=state.cancel_event,
                    )
                )
            else:
                state.stream_task = asyncio.create_task(
                    self._stream_live_llm(
                        session_id=session_id,
                        message_id=message_id,
                        question=question,
                        graph_state=graph_state,
                        cancel_event=state.cancel_event,
                    )
                )

            try:
                await state.stream_task
            except asyncio.CancelledError:
                return

            if state.cancel_event.is_set():
                return

            with Session(get_engine()) as db:
                finalize_assistant_message(
                    db,
                    message_id=message_id,
                    status=MESSAGE_STATUS_COMPLETE,
                )
            publish_chat_event(
                session_id,
                EVENT_GENERATION_COMPLETED,
                {"session_id": session_id, "message_id": message_id},
            )
            # Rehydrate reconnecting clients from DB — pub/sub frames are in-memory only.
            self._publish_session_sync(session_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("agent chat turn failed session_id=%s", session_id)
            self._publish_error(
                session_id,
                code="turn_failed",
                message="Support Agent failed to answer. Try again shortly.",
            )
        finally:
            state.streaming = False
            state.stream_task = None
            state.turn_in_progress = False
            state.current_message_id = None

    def _invoke_graph(
        self,
        *,
        question: str,
        session_id: str,
        user_id: int,
        auth_header: str | None,
    ) -> dict[str, Any]:
        from .graph import invoke_support_agent

        return invoke_support_agent(
            question,
            thread_id=session_id,
            auth_header=auth_header,
            user_id=user_id,
        )

    async def _stream_answer_text(
        self,
        *,
        session_id: str,
        message_id: str,
        answer: str,
        cancel_event: asyncio.Event,
    ) -> None:
        sequence = 0
        for token in chunk_text_for_streaming(answer):
            if cancel_event.is_set():
                return
            sequence += 1
            with Session(get_engine()) as db:
                append_assistant_token(
                    db,
                    message_id=message_id,
                    token=token,
                    sequence=sequence,
                )
            publish_chat_event(
                session_id,
                EVENT_TOKEN_CHUNK,
                {
                    "session_id": session_id,
                    "message_id": message_id,
                    "token": token,
                    "sequence": sequence,
                },
            )
            await asyncio.sleep(0)

    async def _stream_live_llm(
        self,
        *,
        session_id: str,
        message_id: str,
        question: str,
        graph_state: dict[str, Any],
        cancel_event: asyncio.Event,
    ) -> None:
        sequence = 0
        async for token in iter_llm_completion_tokens(question=question, graph_state=graph_state):
            if cancel_event.is_set():
                return
            sequence += 1
            with Session(get_engine()) as db:
                append_assistant_token(
                    db,
                    message_id=message_id,
                    token=token,
                    sequence=sequence,
                )
            publish_chat_event(
                session_id,
                EVENT_TOKEN_CHUNK,
                {
                    "session_id": session_id,
                    "message_id": message_id,
                    "token": token,
                    "sequence": sequence,
                },
            )

    def _publish_session_sync(self, session_id: str) -> None:
        with Session(get_engine()) as db:
            sync_payload = build_session_sync_payload(db, session_id)
        publish_chat_event(session_id, EVENT_SESSION_SYNC, sync_payload)

    def _publish_error(self, session_id: str, *, code: str, message: str) -> None:
        publish_chat_event(
            session_id,
            EVENT_ERROR,
            {"session_id": session_id, "code": code, "message": message},
        )


_orchestrator = AgentChatOrchestrator()


def get_agent_chat_orchestrator() -> AgentChatOrchestrator:
    return _orchestrator


def reset_agent_chat_orchestrator_for_tests() -> None:
    _orchestrator._sessions.clear()


__all__ = [
    "AgentChatOrchestrator",
    "ERROR_TURN_IN_PROGRESS",
    "get_agent_chat_orchestrator",
    "reset_agent_chat_orchestrator_for_tests",
]
