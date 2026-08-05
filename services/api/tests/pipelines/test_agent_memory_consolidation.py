"""Consolidation and injection tests for agent memory (context-26 P26-5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from agent import graph as graph_mod
from agent.memory.location_hint import resolve_injection_location_id
from agent.memory.models import AgentMemoryAuditLog, AgentMemoryEntry
from agent.memory.store import (
    purge_stale_entries,
    read_memory,
    write_memory,
)
from knowledge.bootstrap import ensure_repo_root_on_path
from tests.pipelines.agent_trace_assertions import mock_structured_generation, trace_nodes


@pytest.fixture
def memory_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_MEMORY_CAP_PER_LOCATION", "12")
    monkeypatch.setenv("AGENT_MEMORY_INJECT_MAX_ROWS", "3")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[AgentMemoryEntry.__table__, AgentMemoryAuditLog.__table__],
    )
    with Session(engine) as session:
        yield session


def _write_global(
    session: Session,
    *,
    location_id: int,
    key: str,
    value: str,
    approved_by: int = 1,
    category: str = "hours",
) -> None:
    write_memory(
        session,
        proposal={
            "location_id": location_id,
            "category": category,
            "key": key,
            "value": value,
        },
        approved_by=approved_by,
    )


def _write_pref(session: Session, *, key: str, value: str, approved_by: int) -> None:
    write_memory(
        session,
        proposal={"category": "preferences", "key": key, "value": value},
        approved_by=approved_by,
    )


def test_read_memory_excludes_expired_rows(memory_session: Session):
    row = AgentMemoryEntry(
        location_id=4,
        user_id=None,
        category="suppliers",
        key="meat_delivery_day",
        value="Expired fact",
        source="user_confirmed",
        approved_by=1,
        approved_at=datetime.now(timezone.utc) - timedelta(days=400),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    memory_session.add(row)
    memory_session.commit()

    rows = read_memory(memory_session, location_id=4, user_id=1)
    assert rows == []


def test_expired_rows_do_not_count_toward_location_cap(
    memory_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AGENT_MEMORY_CAP_PER_LOCATION", "1")
    expired = AgentMemoryEntry(
        location_id=8,
        user_id=None,
        category="hours",
        key="weekday_open",
        value="Old hours",
        source="user_confirmed",
        approved_by=1,
        approved_at=datetime.now(timezone.utc) - timedelta(days=400),
        expires_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    memory_session.add(expired)
    memory_session.commit()

    result = write_memory(
        memory_session,
        proposal={
            "location_id": 8,
            "category": "hours",
            "key": "weekday_close",
            "value": "Closes at 10pm",
        },
        approved_by=2,
    )
    assert result.ok is True


def test_upsert_resets_ttl_on_reapprove(memory_session: Session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_MEMORY_TTL_HOURS", "24")
    proposal = {
        "location_id": 3,
        "category": "suppliers",
        "key": "meat_delivery_day",
        "value": "Delivers Tuesdays",
    }
    first = write_memory(memory_session, proposal=proposal, approved_by=5)
    assert first.ok is True

    first_row = memory_session.get(AgentMemoryEntry, first.entry_id)
    assert first_row is not None
    first_expires = first_row.expires_at

    updated = {**proposal, "value": "Delivers Wednesdays"}
    second = write_memory(memory_session, proposal=updated, approved_by=5)
    assert second.ok is True

    second_row = memory_session.get(AgentMemoryEntry, second.entry_id)
    assert second_row is not None
    assert second_row.expires_at is not None
    assert first_expires is not None
    assert second_row.expires_at >= first_expires


def test_read_memory_prioritizes_location_globals_over_preferences(memory_session: Session):
    for index in range(3):
        _write_global(
            memory_session,
            location_id=4,
            key=("weekday_open", "weekday_close", "friday_close")[index],
            value=f"Hours {index}",
        )
    _write_pref(memory_session, key="report_format", value="Bullet points", approved_by=10)
    _write_pref(memory_session, key="summary_style", value="Short summaries", approved_by=10)

    rows = read_memory(memory_session, location_id=4, user_id=10, max_rows=3)
    assert len(rows) == 3
    assert all(row.location_id == 4 for row in rows)


def test_read_memory_includes_preferences_when_room(memory_session: Session):
    _write_global(
        memory_session,
        location_id=4,
        key="weekday_open",
        value="Opens 10am",
    )
    _write_pref(memory_session, key="report_format", value="Bullet points", approved_by=10)

    rows = read_memory(memory_session, location_id=4, user_id=10, max_rows=3)
    assert len(rows) == 2
    categories = {row.category for row in rows}
    assert categories == {"hours", "preferences"}


def test_read_memory_preferences_without_location_hint(memory_session: Session):
    _write_pref(memory_session, key="language_preference", value="English summaries", approved_by=3)
    rows = read_memory(memory_session, user_id=3)
    assert len(rows) == 1
    assert rows[0].category == "preferences"


def test_resolve_injection_location_id_from_inventory_question():
    location_id = resolve_injection_location_id("Stock for beef at Chapinero")
    assert location_id == 4


def test_resolve_injection_location_id_from_pending_proposal():
    location_id = resolve_injection_location_id(
        "Remember that?",
        pending_proposal={
            "location_id": 8,
            "category": "suppliers",
            "key": "meat_delivery_day",
            "value": "Wednesdays",
        },
    )
    assert location_id == 8


def test_purge_stale_entries_removes_old_expired_rows(memory_session: Session):
    stale = AgentMemoryEntry(
        location_id=1,
        user_id=None,
        category="hours",
        key="weekday_open",
        value="Stale",
        source="user_confirmed",
        approved_by=1,
        expires_at=datetime.now(timezone.utc) - timedelta(days=60),
    )
    fresh = AgentMemoryEntry(
        location_id=1,
        user_id=None,
        category="hours",
        key="weekday_close",
        value="Fresh",
        source="user_confirmed",
        approved_by=1,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    memory_session.add(stale)
    memory_session.add(fresh)
    memory_session.commit()

    removed = purge_stale_entries(memory_session, grace_days=30)
    assert removed == 1
    from sqlmodel import select

    remaining = memory_session.exec(select(AgentMemoryEntry)).all()
    assert len(remaining) == 1
    assert remaining[0].key == "weekday_close"


def test_graph_injects_memory_context_into_structured_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    monkeypatch.setenv("AGENT_CHECKPOINT_DB_PATH", str(tmp_path / "checkpoints.db"))
    monkeypatch.setenv("DATABASE_URL", "sqlite://")

    import config
    import database

    monkeypatch.setattr(config, "DATABASE_URL", "sqlite://")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[AgentMemoryEntry.__table__, AgentMemoryAuditLog.__table__],
    )
    database._engine = None
    database._engine = engine

    graph_mod.get_compiled_graph.cache_clear()
    graph_mod._sqlite_checkpointer.cache_clear()

    with Session(engine) as session:
        write_memory(
            session,
            proposal={
                "location_id": 4,
                "category": "suppliers",
                "key": "meat_delivery_day",
                "value": "Meat supplier delivers on Wednesdays",
            },
            approved_by=21,
        )

    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    captured: dict[str, str] = {}

    def _structured_rag(_question: str, _context: str, **kwargs):
        captured["memory_context"] = kwargs.get("memory_context") or ""
        from agent.memory.schemas import GenerationResult

        return GenerationResult(answer="Delivery is on Wednesdays.", memory_proposal=None)

    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [{"text": "Tuesday", "score": 0.6}])
    monkeypatch.setattr(
        "agent.generation.generate_structured_rag_response",
        _structured_rag,
    )

    state = graph_mod.invoke_support_agent(
        "When does the meat supplier deliver at Chapinero?",
        user_id=21,
    )

    nodes = trace_nodes(state)
    assert "read_memory" in nodes
    assert "Wednesdays" in captured.get("memory_context", "")
