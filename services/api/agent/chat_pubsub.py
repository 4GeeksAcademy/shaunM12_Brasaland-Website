"""In-memory pub/sub fan-out for agent chat WebSocket sessions."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

EVENT_SESSION_SYNC = "session_sync"
EVENT_TOKEN_CHUNK = "token_chunk"
EVENT_GENERATION_COMPLETED = "generation_completed"
EVENT_GENERATION_INTERRUPTED = "generation_interrupted"
EVENT_ERROR = "error"
EVENT_USER_MESSAGE = "user_message"
EVENT_INTERRUPT_REQUESTED = "interrupt_requested"


def format_chat_frame(event: str, data: dict[str, Any]) -> str:
    """Serialize one WebSocket JSON frame."""
    return json.dumps({"event": event, "data": data}, separators=(",", ":"), ensure_ascii=False)


class AgentChatPubSub:
    """Per-session subscriber queues (single API worker)."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[str]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, session_id: str) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subscribers.setdefault(session_id, set()).add(queue)
        return queue

    async def unsubscribe(self, session_id: str, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(session_id)
            if not subscribers:
                return
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(session_id, None)

    def publish(self, session_id: str, frame: str) -> None:
        """Fan-out one pre-formatted frame to all subscribers on ``session_id``."""
        subscribers = self._subscribers.get(session_id)
        if not subscribers:
            return
        for queue in list(subscribers):
            try:
                queue.put_nowait(frame)
            except asyncio.QueueFull:
                logger.warning(
                    "Dropping agent chat frame for slow subscriber session_id=%s",
                    session_id,
                )

    def subscriber_count(self, session_id: str) -> int:
        return len(self._subscribers.get(session_id, set()))


_pubsub = AgentChatPubSub()


def get_agent_chat_pubsub() -> AgentChatPubSub:
    return _pubsub


def reset_agent_chat_pubsub_for_tests() -> None:
    _pubsub._subscribers.clear()


def publish_chat_event(session_id: str, event: str, data: dict[str, Any]) -> None:
    _pubsub.publish(session_id, format_chat_frame(event, data))


__all__ = [
    "AgentChatPubSub",
    "EVENT_ERROR",
    "EVENT_GENERATION_COMPLETED",
    "EVENT_GENERATION_INTERRUPTED",
    "EVENT_INTERRUPT_REQUESTED",
    "EVENT_SESSION_SYNC",
    "EVENT_TOKEN_CHUNK",
    "EVENT_USER_MESSAGE",
    "format_chat_frame",
    "get_agent_chat_pubsub",
    "publish_chat_event",
    "reset_agent_chat_pubsub_for_tests",
]
