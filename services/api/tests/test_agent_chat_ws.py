"""Agent chat WebSocket tests (context-28 Milestone 10 Part 2 — Phase 1)."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from uuid import UUID, uuid4

import config
import pytest
from sqlmodel import Session

from agent.chat_models import MESSAGE_STATUS_INTERRUPTED, ensure_agent_chat_schema
from agent.chat_orchestrator import reset_agent_chat_orchestrator_for_tests
from agent.chat_pubsub import (
    EVENT_GENERATION_COMPLETED,
    EVENT_GENERATION_INTERRUPTED,
    EVENT_SESSION_SYNC,
    EVENT_TOKEN_CHUNK,
    format_chat_frame,
    reset_agent_chat_pubsub_for_tests,
)
from agent.chat_repository import (
    create_session_on_connect,
    create_user_message,
    get_message,
    new_message_id,
)
from auth.security import create_access_token
from database import get_engine

pytestmark_db = pytest.mark.skipif(
    not config.DATABASE_URL,
    reason="DATABASE_URL not set — agent chat WS integration tests require PostgreSQL",
)


@pytest.fixture(autouse=True)
def _reset_chat_runtime():
    reset_agent_chat_pubsub_for_tests()
    reset_agent_chat_orchestrator_for_tests()
    yield
    reset_agent_chat_pubsub_for_tests()
    reset_agent_chat_orchestrator_for_tests()


def _register_and_token(client) -> tuple[int, str]:
    client.post(
        "/auth/register",
        json={"email": "chat-user@brasaland.com", "password": "supersecret"},
    )
    login = client.post(
        "/auth/login",
        data={"username": "chat-user@brasaland.com", "password": "supersecret"},
    )
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    return int(me["id"]), token


def _register_second_user(client) -> tuple[int, str]:
    client.post(
        "/auth/register",
        json={"email": "chat-other@brasaland.com", "password": "supersecret"},
    )
    login = client.post(
        "/auth/login",
        data={"username": "chat-other@brasaland.com", "password": "supersecret"},
    )
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    return int(me["id"]), token


def _ws_url(session_id: str, access_token: str | None) -> str:
    token_part = f"&access_token={access_token}" if access_token else ""
    return f"/agent/chat/ws?session_id={session_id}{token_part}"


def _ensure_schema():
    with Session(get_engine()) as session:
        ensure_agent_chat_schema(session)


def _mock_graph(monkeypatch: pytest.MonkeyPatch, answer: str = "For Miami use standard hours."):
    def _fake_invoke(question, *, thread_id=None, auth_header=None, user_id=None):
        return {"answer": answer, "route": "generate", "question": question}

    monkeypatch.setattr("agent.graph.invoke_support_agent", _fake_invoke)


def _mock_slow_chunks(monkeypatch: pytest.MonkeyPatch, tokens: list[str]):
    monkeypatch.setattr("agent.chat_orchestrator.chunk_text_for_streaming", lambda _text: tokens)


@pytest.mark.anyio
async def test_agent_chat_ws_requires_auth(anon_client):
    session_id = str(uuid4())
    with pytest.raises(Exception):
        with anon_client.websocket_connect(_ws_url(session_id, None)):
            pass


@pytest.mark.anyio
@pytestmark_db
async def test_agent_chat_ws_owner_only(anon_client, monkeypatch: pytest.MonkeyPatch):
    _ensure_schema()
    session_id = str(uuid4())
    owner_id, owner_token = _register_and_token(anon_client)
    with Session(get_engine()) as session:
        create_session_on_connect(session, session_id=session_id, user_id=owner_id)

    _, other_token = _register_second_user(anon_client)
    with pytest.raises(Exception):
        with anon_client.websocket_connect(_ws_url(session_id, other_token)):
            pass


@pytest.mark.anyio
@pytestmark_db
async def test_agent_chat_ws_event_wire_format(anon_client, monkeypatch: pytest.MonkeyPatch):
    _ensure_schema()
    _mock_graph(monkeypatch)
    _mock_slow_chunks(monkeypatch, ["For ", "Miami"])
    session_id = str(uuid4())
    _, token = _register_and_token(anon_client)

    with anon_client.websocket_connect(_ws_url(session_id, token)) as ws:
        sync = json.loads(ws.receive_text())
        assert sync["event"] == EVENT_SESSION_SYNC
        assert sync["data"]["session_id"] == session_id
        assert sync["data"]["messages"] == []

        ws.send_text(
            json.dumps(
                {
                    "event": "user_message",
                    "data": {"session_id": session_id, "content": "Miami hours?"},
                }
            )
        )

        seen_token = False
        deadline = time.time() + 5.0
        while time.time() < deadline:
            frame = json.loads(ws.receive_text())
            assert "event" in frame
            assert "data" in frame
            event = frame["event"]
            data = frame["data"]
            assert data["session_id"] == session_id
            if event == EVENT_TOKEN_CHUNK:
                seen_token = True
                assert {"message_id", "token", "sequence"} <= set(data.keys())
                UUID(data["message_id"])
            if event == EVENT_GENERATION_COMPLETED:
                assert "message_id" in data
                break
        assert seen_token


@pytest.mark.anyio
@pytestmark_db
async def test_token_chunk_sequence_increments(anon_client, monkeypatch: pytest.MonkeyPatch):
    _ensure_schema()
    _mock_graph(monkeypatch)
    _mock_slow_chunks(monkeypatch, ["One", " Two", " Three"])
    session_id = str(uuid4())
    _, token = _register_and_token(anon_client)

    with anon_client.websocket_connect(_ws_url(session_id, token)) as ws:
        ws.receive_text()
        ws.send_text(
            json.dumps(
                {
                    "event": "user_message",
                    "data": {"session_id": session_id, "content": "Count tokens"},
                }
            )
        )

        sequences: list[int] = []
        message_id: str | None = None
        deadline = time.time() + 5.0
        while time.time() < deadline:
            frame = json.loads(ws.receive_text())
            if frame["event"] != EVENT_TOKEN_CHUNK:
                continue
            data = frame["data"]
            message_id = data["message_id"]
            sequences.append(int(data["sequence"]))
            # sequence 0 = empty turn-start marker; then one chunk per mocked token.
            if len(sequences) == 4:
                break

        assert message_id is not None
        assert sequences == [0, 1, 2, 3]


@pytest.mark.anyio
@pytestmark_db
async def test_interrupt_stops_token_chunks(anon_client, monkeypatch: pytest.MonkeyPatch):
    _ensure_schema()
    _mock_graph(monkeypatch, answer="alpha beta gamma delta epsilon")
    tokens = [f"t{i}" for i in range(30)]

    async def delayed_stream(self, **kwargs):
        sequence = 0
        for token in tokens:
            if kwargs["cancel_event"].is_set():
                return
            sequence += 1
            with Session(get_engine()) as db:
                append_assistant_token(
                    db,
                    message_id=kwargs["message_id"],
                    token=token,
                    sequence=sequence,
                )
            publish_chat_event(
                kwargs["session_id"],
                EVENT_TOKEN_CHUNK,
                {
                    "session_id": kwargs["session_id"],
                    "message_id": kwargs["message_id"],
                    "token": token,
                    "sequence": sequence,
                },
            )
            await asyncio.sleep(0.08)

    from agent.chat_orchestrator import AgentChatOrchestrator
    from agent.chat_repository import append_assistant_token
    from agent.chat_pubsub import publish_chat_event

    monkeypatch.setattr(AgentChatOrchestrator, "_stream_answer_text", delayed_stream)

    session_id = str(uuid4())
    _, token = _register_and_token(anon_client)

    with anon_client.websocket_connect(_ws_url(session_id, token)) as ws:
        ws.receive_text()
        ws.send_text(
            json.dumps(
                {
                    "event": "user_message",
                    "data": {"session_id": session_id, "content": "Start long stream"},
                }
            )
        )

        first_message_id = None
        chunk_count = 0
        deadline = time.time() + 8.0
        while time.time() < deadline and chunk_count < 3:
            frame = json.loads(ws.receive_text())
            if frame["event"] == EVENT_TOKEN_CHUNK:
                first_message_id = frame["data"]["message_id"]
                chunk_count += 1

        assert first_message_id is not None
        ws.send_text(
            json.dumps(
                {
                    "event": "interrupt_requested",
                    "data": {
                        "session_id": session_id,
                        "new_input": "Stop and answer Miami instead",
                    },
                }
            )
        )

        interrupted_seen = False
        extra_old_chunks = 0
        deadline = time.time() + 10.0
        while time.time() < deadline:
            frame = json.loads(ws.receive_text())
            event = frame["event"]
            data = frame["data"]
            if event == EVENT_GENERATION_INTERRUPTED:
                assert data["message_id"] == first_message_id
                interrupted_seen = True
                break
            if event == EVENT_TOKEN_CHUNK and data["message_id"] == first_message_id:
                extra_old_chunks += 1

        assert interrupted_seen
        assert extra_old_chunks == 0


@pytest.mark.anyio
@pytestmark_db
async def test_generation_interrupted_partial_persisted(
    anon_client, monkeypatch: pytest.MonkeyPatch
):
    _ensure_schema()
    _mock_graph(monkeypatch, answer="partial answer text")

    async def delayed_stream(self, **kwargs):
        sequence = 0
        for token in ("partial ", "answer"):
            if kwargs["cancel_event"].is_set():
                return
            sequence += 1
            with Session(get_engine()) as db:
                append_assistant_token(
                    db,
                    message_id=kwargs["message_id"],
                    token=token,
                    sequence=sequence,
                )
            publish_chat_event(
                kwargs["session_id"],
                EVENT_TOKEN_CHUNK,
                {
                    "session_id": kwargs["session_id"],
                    "message_id": kwargs["message_id"],
                    "token": token,
                    "sequence": sequence,
                },
            )
            await asyncio.sleep(0.08)

    from agent.chat_orchestrator import AgentChatOrchestrator
    from agent.chat_repository import append_assistant_token
    from agent.chat_pubsub import publish_chat_event

    monkeypatch.setattr(AgentChatOrchestrator, "_stream_answer_text", delayed_stream)

    session_id = str(uuid4())
    _, token = _register_and_token(anon_client)

    with anon_client.websocket_connect(_ws_url(session_id, token)) as ws:
        ws.receive_text()
        ws.send_text(
            json.dumps(
                {
                    "event": "user_message",
                    "data": {"session_id": session_id, "content": "First question"},
                }
            )
        )

        message_id = None
        deadline = time.time() + 5.0
        while time.time() < deadline:
            frame = json.loads(ws.receive_text())
            if frame["event"] == EVENT_TOKEN_CHUNK:
                message_id = frame["data"]["message_id"]
                break

        assert message_id is not None
        ws.send_text(
            json.dumps(
                {
                    "event": "interrupt_requested",
                    "data": {
                        "session_id": session_id,
                        "new_input": "Redirect question",
                    },
                }
            )
        )

        interrupted_id = None
        deadline = time.time() + 8.0
        while time.time() < deadline:
            frame = json.loads(ws.receive_text())
            if frame["event"] == EVENT_GENERATION_INTERRUPTED:
                interrupted_id = frame["data"]["message_id"]
                break

    assert interrupted_id == message_id
    with Session(get_engine()) as session:
        row = get_message(session, message_id)
        assert row is not None
        assert row.status == MESSAGE_STATUS_INTERRUPTED
        assert row.content.startswith("partial")


@pytest.mark.anyio
@pytestmark_db
async def test_session_sync_on_connect(anon_client, monkeypatch: pytest.MonkeyPatch):
    _ensure_schema()
    session_id = str(uuid4())
    user_id, token = _register_and_token(anon_client)
    with Session(get_engine()) as session:
        create_session_on_connect(session, session_id=session_id, user_id=user_id)
        create_user_message(session, session_id=session_id, content="Earlier question")

    with anon_client.websocket_connect(_ws_url(session_id, token)) as ws:
        sync = json.loads(ws.receive_text())
        assert sync["event"] == EVENT_SESSION_SYNC
        messages = sync["data"]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Earlier question"
        assert messages[0]["status"] == "complete"
        assert messages[0]["created_at"].endswith("Z")


def test_new_message_id_is_uuid_v4():
    message_id = new_message_id()
    parsed = UUID(message_id)
    assert str(parsed) == message_id


def test_chat_frame_helper_wire_shape():
    frame = format_chat_frame(
        EVENT_TOKEN_CHUNK,
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "message_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "token": "For",
            "sequence": 1,
        },
    )
    payload = json.loads(frame)
    assert payload == {
        "event": EVENT_TOKEN_CHUNK,
        "data": {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "message_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "token": "For",
            "sequence": 1,
        },
    }


@pytest.mark.anyio
@pytestmark_db
async def test_pubsub_fanout_single_run(anon_client, monkeypatch: pytest.MonkeyPatch):
    _ensure_schema()
    invoke_calls: list[str] = []

    def _counting_invoke(question, *, thread_id=None, auth_header=None, user_id=None):
        invoke_calls.append(question)
        return {"answer": "Shared fanout answer", "route": "generate"}

    monkeypatch.setattr("agent.graph.invoke_support_agent", _counting_invoke)
    _mock_slow_chunks(monkeypatch, ["Shared ", "fanout"])

    session_id = str(uuid4())
    _, token = _register_and_token(anon_client)

    with anon_client.websocket_connect(_ws_url(session_id, token)) as ws1:
        ws1.receive_text()
        with anon_client.websocket_connect(_ws_url(session_id, token)) as ws2:
            ws2.receive_text()
            ws1.send_text(
                json.dumps(
                    {
                        "event": "user_message",
                        "data": {"session_id": session_id, "content": "Fanout please"},
                    }
                )
            )

            ws1_chunks: list[dict] = []
            ws2_chunks: list[dict] = []
            deadline = time.time() + 8.0
            while time.time() < deadline and (
                len(ws1_chunks) < 2 or len(ws2_chunks) < 2
            ):
                for ws, bucket in ((ws1, ws1_chunks), (ws2, ws2_chunks)):
                    try:
                        frame = json.loads(ws.receive_text())
                    except Exception:
                        continue
                    if frame["event"] == EVENT_TOKEN_CHUNK:
                        bucket.append(frame["data"])

            assert len(invoke_calls) == 1
            assert len(ws1_chunks) >= 2
            assert len(ws2_chunks) >= 2
            assert ws1_chunks[0]["token"] == ws2_chunks[0]["token"]
            assert ws1_chunks[0]["message_id"] == ws2_chunks[0]["message_id"]


@pytest.mark.anyio
@pytestmark_db
async def test_session_sync_fanout_after_user_message(anon_client, monkeypatch: pytest.MonkeyPatch):
    _ensure_schema()
    release = threading.Event()

    def _blocking_invoke(question, *, thread_id=None, auth_header=None, user_id=None):
        release.wait(timeout=5.0)
        return {"answer": "Later answer", "route": "generate"}

    monkeypatch.setattr("agent.graph.invoke_support_agent", _blocking_invoke)
    _mock_slow_chunks(monkeypatch, ["Later"])

    session_id = str(uuid4())
    _, token = _register_and_token(anon_client)

    with anon_client.websocket_connect(_ws_url(session_id, token)) as ws1:
        ws1.receive_text()
        with anon_client.websocket_connect(_ws_url(session_id, token)) as ws2:
            ws2.receive_text()
            ws1.send_text(
                json.dumps(
                    {
                        "event": "user_message",
                        "data": {"session_id": session_id, "content": "Cross-tab question"},
                    }
                )
            )

            ws2_sync = None
            deadline = time.time() + 3.0
            while time.time() < deadline and ws2_sync is None:
                try:
                    frame = json.loads(ws2.receive_text())
                except Exception:
                    continue
                if frame["event"] == EVENT_SESSION_SYNC:
                    ws2_sync = frame["data"]

            release.set()
            assert ws2_sync is not None
            messages = ws2_sync["messages"]
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "Cross-tab question"


@pytest.mark.anyio
@pytestmark_db
async def test_turn_in_progress_error(anon_client, monkeypatch: pytest.MonkeyPatch):
    _ensure_schema()
    release = threading.Event()

    def _blocking_invoke(question, *, thread_id=None, auth_header=None, user_id=None):
        release.wait(timeout=5.0)
        return {"answer": "Done after block", "route": "generate"}

    monkeypatch.setattr("agent.graph.invoke_support_agent", _blocking_invoke)
    _mock_slow_chunks(monkeypatch, ["Done"])

    session_id = str(uuid4())
    _, token = _register_and_token(anon_client)

    with anon_client.websocket_connect(_ws_url(session_id, token)) as ws:
        ws.receive_text()
        ws.send_text(
            json.dumps(
                {
                    "event": "user_message",
                    "data": {"session_id": session_id, "content": "First turn"},
                }
            )
        )
        time.sleep(0.05)

        error_seen = False
        deadline = time.time() + 2.0
        while time.time() < deadline and not error_seen:
            ws.send_text(
                json.dumps(
                    {
                        "event": "user_message",
                        "data": {"session_id": session_id, "content": "Second turn"},
                    }
                )
            )
            frame = json.loads(ws.receive_text())
            if frame["event"] == "error":
                assert frame["data"]["code"] == "turn_in_progress"
                error_seen = True

        release.set()
        assert error_seen


def test_invalid_access_token_rejected(anon_client):
    session_id = str(uuid4())
    bad_token = create_access_token(999999)
    with pytest.raises(Exception):
        with anon_client.websocket_connect(_ws_url(session_id, bad_token)):
            pass
