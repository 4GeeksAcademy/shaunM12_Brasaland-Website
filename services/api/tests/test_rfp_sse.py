"""RFP SSE endpoint tests (context-28 Milestone 10 Part 1 — Phase 1)."""

from __future__ import annotations

import asyncio
import json

import config
import pytest

from rfp.constants import STATUS_ANALYZING
from rfp.repository import create_ticket_analyzing
from rfp.sse import (
    RFP_SSE_EVENT_TICKET_CREATED,
    RfpSseBroadcaster,
    build_rfp_ticket_created_payload,
    format_sse_event,
    publish_rfp_ticket_created,
    reset_rfp_sse_broadcaster_for_tests,
    stream_rfp_events,
)
from database import get_engine
from rfp.models import ensure_rfp_schema
from sqlmodel import Session

pytestmark_db = pytest.mark.skipif(
    not config.DATABASE_URL,
    reason="DATABASE_URL not set — RFP SSE integration tests require PostgreSQL",
)


@pytest.fixture(autouse=True)
def _reset_sse_broadcaster():
    reset_rfp_sse_broadcaster_for_tests()
    yield
    reset_rfp_sse_broadcaster_for_tests()


def _stub_generation_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GENERATION_BASE_URL", "http://gen.test/v1")
    monkeypatch.setenv("GENERATION_API_KEY", "test-key")
    monkeypatch.setenv("GENERATION_MODEL_ID", "test-model")
    monkeypatch.setattr(config, "GENERATION_BASE_URL", "http://gen.test/v1")
    monkeypatch.setattr(config, "GENERATION_API_KEY", "test-key")
    monkeypatch.setattr(config, "GENERATION_MODEL_ID", "test-model")


def _parse_sse_data_line(body: str) -> dict:
    for line in body.splitlines():
        if line.startswith("data:"):
            return json.loads(line.removeprefix("data:").strip())
    raise AssertionError(f"No SSE data line found in frame: {body!r}")


class _DisconnectAfterFirstFrame:
    """Minimal request stub that ends the SSE loop after one keep-alive."""

    def __init__(self) -> None:
        self._checks = 0

    async def is_disconnected(self) -> bool:
        self._checks += 1
        return self._checks > 1


def test_rfp_sse_requires_auth(anon_client):
    assert anon_client.get("/rfp/events/stream").status_code == 401


def test_rfp_sse_wire_format_helpers():
    frame = format_sse_event(
        RFP_SSE_EVENT_TICKET_CREATED,
        {
            "ticket_id": "tkt-test",
            "status": STATUS_ANALYZING,
            "created_at": "2026-07-24T14:32:00Z",
            "client_name": None,
            "location": None,
            "service_type": None,
        },
    )
    assert frame.startswith("event: rfp_ticket_created\n")
    assert "data:" in frame
    payload = _parse_sse_data_line(frame)
    assert payload["ticket_id"] == "tkt-test"
    assert payload["status"] == STATUS_ANALYZING
    assert payload["created_at"] == "2026-07-24T14:32:00Z"


def test_rfp_sse_stream_response_metadata():
    response = stream_rfp_events(_DisconnectAfterFirstFrame())
    assert response.media_type == "text/event-stream"
    assert response.headers.get("cache-control") == "no-cache"


@pytest.mark.anyio
async def test_rfp_sse_broadcaster_fanout():
    broadcaster = RfpSseBroadcaster()
    queue = await broadcaster.subscribe()
    frame = format_sse_event(
        RFP_SSE_EVENT_TICKET_CREATED,
        {
            "ticket_id": "broadcast-test",
            "status": STATUS_ANALYZING,
            "created_at": "2026-07-24T14:32:00Z",
            "client_name": None,
            "location": None,
            "service_type": None,
        },
    )
    broadcaster.publish(frame)
    received = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert received == frame
    await broadcaster.unsubscribe(queue)


@pytest.mark.anyio
async def test_rfp_sse_stream_emits_keep_alive_then_exits():
    from rfp.sse import iter_rfp_sse_events

    chunks: list[str] = []
    async for chunk in iter_rfp_sse_events(_DisconnectAfterFirstFrame()):
        chunks.append(chunk)
    assert chunks
    assert chunks[0].startswith(": keep-alive")


@pytest.mark.usefixtures("_rfp_ticket_cleanup_autouse")
def test_post_rfp_ticket_publishes_sse_event(client, monkeypatch):
    if not config.DATABASE_URL:
        pytest.skip("DATABASE_URL required for this test")
    _stub_generation_env(monkeypatch)
    monkeypatch.setattr(
        "rfp.routes.run_intake_background_task",
        lambda ticket_id: None,
    )

    published: list[str] = []

    def _capture_publish(ticket) -> None:
        published.append(ticket.ticket_id)
        frame = format_sse_event(
            RFP_SSE_EVENT_TICKET_CREATED,
            build_rfp_ticket_created_payload(ticket),
        )
        assert frame.startswith("event: rfp_ticket_created\n")
        assert "data:" in frame
        payload = _parse_sse_data_line(frame)
        assert payload["status"] == STATUS_ANALYZING
        assert "created_at" in payload

    monkeypatch.setattr("rfp.routes.publish_rfp_ticket_created", _capture_publish)

    post_response = client.post(
        "/rfp/tickets",
        files={"file": ("sample.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert post_response.status_code == 201
    body = post_response.json()
    assert published == [body["ticket_id"]]


def test_publish_not_on_failed_upload(client, monkeypatch):
    if not config.DATABASE_URL:
        pytest.skip("DATABASE_URL required for this test")
    _stub_generation_env(monkeypatch)

    published: list[str] = []

    def _capture_publish(ticket) -> None:
        published.append(ticket.ticket_id)

    monkeypatch.setattr("rfp.routes.publish_rfp_ticket_created", _capture_publish)

    response = client.post(
        "/rfp/tickets",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert published == []


def test_publish_rfp_ticket_created_reaches_global_broadcaster():
    if not config.DATABASE_URL:
        pytest.skip("DATABASE_URL required for this test")

    async def _run() -> str:
        from rfp.sse import get_rfp_sse_broadcaster

        queue = await get_rfp_sse_broadcaster().subscribe()
        with Session(get_engine()) as session:
            ensure_rfp_schema(session)
            ticket = create_ticket_analyzing(session, ticket_id="publish-hook-test")
        publish_rfp_ticket_created(ticket)
        frame = await asyncio.wait_for(queue.get(), timeout=1.0)
        await get_rfp_sse_broadcaster().unsubscribe(queue)
        return frame

    frame = asyncio.run(_run())
    assert "event: rfp_ticket_created" in frame
    payload = _parse_sse_data_line(frame)
    assert payload["ticket_id"] == "publish-hook-test"


def test_build_rfp_ticket_created_payload_uses_ticket_fields():
    if not config.DATABASE_URL:
        pytest.skip("DATABASE_URL required for this test")

    with Session(get_engine()) as session:
        ensure_rfp_schema(session)
        ticket = create_ticket_analyzing(
            session,
            ticket_id="payload-shape-test-id",
        )
        ticket.metadata_json = {
            "client_name": "Andes Tech Solutions",
            "location": "Medellín",
            "service_type": "recurring_catering",
        }
        session.add(ticket)
        session.commit()
        session.refresh(ticket)

    payload = build_rfp_ticket_created_payload(ticket)
    assert set(payload.keys()) >= {
        "ticket_id",
        "status",
        "created_at",
        "client_name",
        "location",
        "service_type",
    }
    assert payload["ticket_id"] == "payload-shape-test-id"
    assert payload["client_name"] == "Andes Tech Solutions"
