"""Rate limit and audit tests for memory proposals (context-26 P26-L4h, P26-4)."""

from __future__ import annotations

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from agent.memory.models import AgentMemoryAuditLog, AgentMemoryEntry
from agent.memory.schemas import MemoryProposal
from agent.memory.store import (
    check_proposal_rate_limit,
    count_recent_proposed,
    log_proposal,
    proposal_rate_limit,
)


@pytest.fixture
def memory_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_MEMORY_PROPOSAL_RATE_LIMIT", "3")
    monkeypatch.setenv("AGENT_MEMORY_PROPOSAL_RATE_WINDOW_HOURS", "24")
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


def _proposal(key: str = "meat_delivery_day") -> MemoryProposal:
    return MemoryProposal(
        location_id=3,
        category="suppliers",
        key=key,
        value="Meat supplier delivers on Wednesdays",
    )


def test_proposal_rate_limit_defaults():
    assert proposal_rate_limit() == 20


def test_count_recent_proposed_only_counts_proposed_outcome(memory_session: Session):
    proposal = _proposal()
    log_proposal(memory_session, user_id=5, outcome="proposed", proposal=proposal)
    log_proposal(memory_session, user_id=5, outcome="proposed", proposal=proposal)
    log_proposal(memory_session, user_id=5, outcome="rejected", proposal=proposal)

    assert count_recent_proposed(memory_session, user_id=5) == 2


def test_check_proposal_rate_limit_blocks_at_limit(memory_session: Session):
    proposal = _proposal()
    for _ in range(3):
        log_proposal(memory_session, user_id=9, outcome="proposed", proposal=proposal)

    rate = check_proposal_rate_limit(memory_session, user_id=9)
    assert rate.allowed is False
    assert rate.count == 3
    assert rate.limit == 3


def test_check_proposal_rate_limit_allows_under_limit(memory_session: Session):
    log_proposal(
        memory_session,
        user_id=12,
        outcome="proposed",
        proposal=_proposal(),
    )
    rate = check_proposal_rate_limit(memory_session, user_id=12)
    assert rate.allowed is True
    assert rate.count == 1


def test_graph_validate_output_logs_proposed_and_stages_pending(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    from agent import graph as graph_mod
    from knowledge.bootstrap import ensure_repo_root_on_path

    monkeypatch.setenv("AGENT_CHECKPOINT_DB_PATH", str(tmp_path / "checkpoints.db"))
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("AGENT_MEMORY_PROPOSAL_RATE_LIMIT", "3")

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

    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod
    from tests.pipelines.agent_trace_assertions import mock_structured_generation

    proposal = {
        "location_id": 3,
        "category": "suppliers",
        "key": "meat_delivery_day",
        "value": "Meat supplier delivers on Wednesdays",
    }
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [{"text": "Tuesday", "score": 0.6}])
    mock_structured_generation(
        monkeypatch,
        rag_answer="Wednesdays. Remember that?",
        rag_proposal=proposal,
    )

    state = graph_mod.invoke_support_agent("Supplier day correction", user_id=55)
    assert state.get("pending_proposal") is not None

    with Session(engine) as session:
        rows = session.exec(
            select(AgentMemoryAuditLog).where(AgentMemoryAuditLog.user_id == 55)
        ).all()
        assert len(rows) == 1
        assert rows[0].outcome == "proposed"


def test_graph_validate_output_rate_limit_suppresses_pending(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    from agent import graph as graph_mod
    from knowledge.bootstrap import ensure_repo_root_on_path

    monkeypatch.setenv("AGENT_CHECKPOINT_DB_PATH", str(tmp_path / "checkpoints.db"))
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("AGENT_MEMORY_PROPOSAL_RATE_LIMIT", "1")

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

    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod
    from tests.pipelines.agent_trace_assertions import mock_structured_generation

    proposal = {
        "location_id": 3,
        "category": "suppliers",
        "key": "meat_delivery_day",
        "value": "Meat supplier delivers on Wednesdays",
    }
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [{"text": "x", "score": 0.6}])
    mock_structured_generation(
        monkeypatch,
        rag_answer="Remember?",
        rag_proposal=proposal,
    )

    first = graph_mod.invoke_support_agent(
        "Envigado meat supplier delivers on Wednesdays, not Tuesdays.",
        user_id=88,
    )
    assert first.get("pending_proposal") is not None

    second = graph_mod.invoke_support_agent(
        "Orlando general supplier deliveries are on Mondays, not Wednesdays.",
        user_id=88,
    )
    assert second.get("pending_proposal") is None

    with Session(engine) as session:
        rows = session.exec(
            select(AgentMemoryAuditLog)
            .where(AgentMemoryAuditLog.user_id == 88)
            .order_by(AgentMemoryAuditLog.id)
        ).all()
        assert [row.outcome for row in rows] == ["proposed", "rejected_rate_limit"]
