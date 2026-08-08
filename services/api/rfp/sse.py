"""RFP Server-Sent Events broadcaster (context-28 Milestone 10 Part 1)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import timezone
from typing import Any

from fastapi import Request
from fastapi.responses import StreamingResponse

from .constants import STATUS_ANALYZING
from .models import RfpTicket

logger = logging.getLogger(__name__)

RFP_SSE_EVENT_TICKET_CREATED = "rfp_ticket_created"
KEEP_ALIVE_INTERVAL_SECONDS = 25.0
SSE_MEDIA_TYPE = "text/event-stream"


def build_rfp_ticket_created_payload(ticket: RfpTicket) -> dict[str, Any]:
    """Build the JSON object placed on the SSE ``data:`` line."""
    meta = ticket.metadata_json or {}
    created_at = ticket.created_at
    if created_at.tzinfo is not None:
        created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)
    return {
        "ticket_id": ticket.ticket_id,
        "status": ticket.status or STATUS_ANALYZING,
        "created_at": f"{created_at.isoformat()}Z",
        "client_name": meta.get("client_name"),
        "location": meta.get("location"),
        "service_type": meta.get("service_type"),
    }


def format_sse_event(event: str, data: dict[str, Any]) -> str:
    """Format one named SSE event frame."""
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def format_keep_alive() -> str:
    """SSE comment frame to keep intermediaries from closing idle connections."""
    return ": keep-alive\n\n"


class RfpSseBroadcaster:
    """In-process fan-out for RFP SSE subscribers (single API worker)."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    def publish(self, frame: str) -> None:
        """Fan-out one pre-formatted SSE frame to all subscriber queues."""
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(frame)
            except asyncio.QueueFull:
                logger.warning("Dropping RFP SSE frame for a slow subscriber")

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


_broadcaster = RfpSseBroadcaster()


def get_rfp_sse_broadcaster() -> RfpSseBroadcaster:
    return _broadcaster


def reset_rfp_sse_broadcaster_for_tests() -> None:
    """Clear subscribers between tests."""
    _broadcaster._subscribers.clear()


def publish_rfp_ticket_created(ticket: RfpTicket) -> None:
    """Emit ``rfp_ticket_created`` to all active SSE connections."""
    payload = build_rfp_ticket_created_payload(ticket)
    frame = format_sse_event(RFP_SSE_EVENT_TICKET_CREATED, payload)
    _broadcaster.publish(frame)
    logger.info("Published RFP SSE event ticket_id=%s", ticket.ticket_id)


async def iter_rfp_sse_events(request: Request) -> AsyncIterator[str]:
    """Yield SSE frames for one connected client until disconnect."""
    queue = await _broadcaster.subscribe()
    try:
        yield format_keep_alive()
        while True:
            if await request.is_disconnected():
                break
            try:
                frame = await asyncio.wait_for(
                    queue.get(),
                    timeout=KEEP_ALIVE_INTERVAL_SECONDS,
                )
            except asyncio.TimeoutError:
                frame = format_keep_alive()
            yield frame
    finally:
        await _broadcaster.unsubscribe(queue)


def stream_rfp_events(request: Request) -> StreamingResponse:
    """Return a long-lived ``text/event-stream`` response."""
    return StreamingResponse(
        iter_rfp_sse_events(request),
        media_type=SSE_MEDIA_TYPE,
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = [
    "KEEP_ALIVE_INTERVAL_SECONDS",
    "RFP_SSE_EVENT_TICKET_CREATED",
    "RfpSseBroadcaster",
    "build_rfp_ticket_created_payload",
    "format_keep_alive",
    "format_sse_event",
    "get_rfp_sse_broadcaster",
    "iter_rfp_sse_events",
    "publish_rfp_ticket_created",
    "reset_rfp_sse_broadcaster_for_tests",
    "stream_rfp_events",
]
