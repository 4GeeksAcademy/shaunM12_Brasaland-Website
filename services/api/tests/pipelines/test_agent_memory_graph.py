"""Support Agent memory graph integration tests (context-26 P26-3)."""

from __future__ import annotations

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from agent import graph as graph_mod
from agent.memory.models import AgentMemoryAuditLog, AgentMemoryEntry
from agent.state import initial_state
from knowledge.bootstrap import ensure_repo_root_on_path
from tests.pipelines.agent_trace_assertions import (
    assert_guardrail_prefix,
    mock_structured_generation,
    trace_nodes,
)


@pytest.fixture(autouse=True)
def _agent_memory_graph_env(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("AGENT_CHECKPOINT_DB_PATH", str(tmp_path / "checkpoints.db"))
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "http://embed.test/v1")
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-embed-key")
    monkeypatch.setenv("EMBEDDING_MODEL_ID", "test/embed-model")
    monkeypatch.setenv("GENERATION_BASE_URL", "http://gen.test/v1")
    monkeypatch.setenv("GENERATION_API_KEY", "test-gen-key")
    monkeypatch.setenv("GENERATION_MODEL_ID", "test/chat-model")
    monkeypatch.setenv("RAG_MIN_SCORE", "0.30")
    monkeypatch.setenv("AGENT_MEMORY_CAP_PER_LOCATION", "12")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[AgentMemoryEntry.__table__, AgentMemoryAuditLog.__table__],
    )
    monkeypatch.setenv("DATABASE_URL", "sqlite://")

    import config
    import database

    monkeypatch.setattr(config, "DATABASE_URL", "sqlite://")
    database._engine = None
    database._engine = engine

    graph_mod.get_compiled_graph.cache_clear()
    graph_mod._sqlite_checkpointer.cache_clear()
    yield
    graph_mod.get_compiled_graph.cache_clear()
    graph_mod._sqlite_checkpointer.cache_clear()
    database._engine = None


def test_initial_state_includes_memory_fields():
    state = initial_state("supplier delivery day")
    assert state["memory_context"] == ""
    assert state["pending_proposal"] is None
    assert state["pending_proposal_at"] is None
    assert state["memory_proposal_candidate"] is None
    assert state["memory_notice"] is None


def test_memory_nodes_in_trace_order(monkeypatch: pytest.MonkeyPatch):
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    chunks = [
        {
            "source_document": "brasaland-loyalty-program.en.md",
            "section": "Gold tier",
            "text": "Gold requires 50+ points.",
            "score": 0.55,
        }
    ]
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: chunks)
    mock_structured_generation(
        monkeypatch,
        rag_answer="Gold tier requires 50 or more loyalty points.",
    )

    state = graph_mod.invoke_support_agent("How many points for Gold tier?", user_id=1)
    nodes = trace_nodes(state)

    assert_guardrail_prefix(nodes)
    assert state["route"] == "generate"


def test_pending_proposal_survives_thread_across_invokes(monkeypatch: pytest.MonkeyPatch):
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    proposal = {
        "location_id": 3,
        "category": "suppliers",
        "key": "meat_delivery_day",
        "value": "Meat supplier delivers on Wednesdays",
        "reason": "User correction",
    }
    chunks = [
        {
            "source_document": "doc.md",
            "section": "Delivery",
            "text": "Default Tuesday delivery.",
            "score": 0.6,
        }
    ]
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: chunks)
    mock_structured_generation(
        monkeypatch,
        rag_answer="Delivery is on Wednesdays. Want me to remember that for next time?",
        rag_proposal=proposal,
    )

    thread_id = "test-thread-pending-001"
    first = graph_mod.invoke_support_agent(
        "Envigado meat supplier delivers Wednesdays not Tuesdays",
        thread_id=thread_id,
        user_id=42,
    )
    assert first["pending_proposal"] is not None
    assert first["pending_proposal"]["key"] == "meat_delivery_day"

    mock_structured_generation(
        monkeypatch,
        rag_answer="Gold tier requires 50 or more loyalty points.",
    )
    second = graph_mod.invoke_support_agent(
        "Yes, remember that",
        thread_id=thread_id,
        user_id=42,
    )

    nodes = trace_nodes(second)
    assert "resolve_memory_proposal" in nodes
    assert second["route"] == "memory_ack"
    assert "remember" in second["answer"].lower()
    assert second.get("pending_proposal") is None


def test_approve_and_continue_same_message(monkeypatch: pytest.MonkeyPatch):
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    proposal = {
        "location_id": 3,
        "category": "suppliers",
        "key": "meat_delivery_day",
        "value": "Meat supplier delivers on Wednesdays",
    }
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [])
    monkeypatch.setattr(
        rag_mod,
        "assemble_context",
        lambda _chunks: "## Untrusted retrieved documents\nDefault Tuesday.",
    )

    mock_structured_generation(
        monkeypatch,
        rag_answer="Wednesdays. Remember?",
        rag_proposal=proposal,
        support_answer="There are 2 open incidents.",
    )
    monkeypatch.setattr(
        graph_mod,
        "lookup_incidents_via_mcp",
        lambda **_kwargs: {
            "source": "incidents_api",
            "ok": True,
            "rows": [{"id": 1, "status": "open", "branch": "miami_doral"}],
            "summary": "1 open incident",
        },
    )

    thread_id = "test-thread-approve-ops"
    graph_mod.invoke_support_agent(
        "Envigado meat supplier delivers on Wednesdays, not Tuesdays.",
        thread_id=thread_id,
        user_id=7,
    )

    state = graph_mod.invoke_support_agent(
        "Yes, remember that — list open incidents",
        thread_id=thread_id,
        user_id=7,
    )

    nodes = trace_nodes(state)
    assert "resolve_memory_proposal" in nodes
    assert "classify" in nodes
    assert "lookup_incident" in nodes
    assert state.get("pending_proposal") is None
    assert state["route"] in {"generate", "fallback"}


def test_topic_change_while_pending_prepends_notice_and_continues(
    monkeypatch: pytest.MonkeyPatch,
):
    """Cycle C: drop pending memory but still answer the new ops question."""
    ensure_repo_root_on_path()
    from agent.memory.constants import MEMORY_REJECT_TOPIC_CHANGE_MESSAGE
    from data.pipelines import rag as rag_mod

    proposal = {
        "location_id": 12,
        "category": "suppliers",
        "key": "meat_delivery_day",
        "value": "Meat supplier delivers on Wednesdays",
    }
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [{"text": "x", "score": 0.5}])
    mock_structured_generation(
        monkeypatch,
        rag_answer="Wednesdays. Would you like me to remember this local exception?",
        rag_proposal=proposal,
        support_answer="Open incidents at Miami Doral: #104 Broken POS.",
    )
    monkeypatch.setattr(
        graph_mod,
        "lookup_incidents_via_mcp",
        lambda **_kwargs: {
            "source": "incidents_api",
            "ok": True,
            "rows": [{"id": 104, "status": "open", "branch": "miami_doral"}],
            "summary": "1 open incident",
        },
    )

    thread_id = "test-thread-topic-change"
    graph_mod.invoke_support_agent(
        "Tampa Bay meat supplier delivers on Wednesdays, not Tuesdays.",
        thread_id=thread_id,
        user_id=9,
    )

    state = graph_mod.invoke_support_agent(
        "List open incidents at Miami Doral",
        thread_id=thread_id,
        user_id=9,
    )

    nodes = trace_nodes(state)
    assert "resolve_memory_proposal" in nodes
    assert "lookup_incident" in nodes
    assert "memory_reject" not in nodes
    assert state.get("pending_proposal") is None
    assert state["answer"].startswith(MEMORY_REJECT_TOPIC_CHANGE_MESSAGE)
    assert "#104" in state["answer"] or "Broken POS" in state["answer"]
    assert state["last_memory_outcome"] == "rejected_ambiguous"


def test_denylist_edit_on_approve_returns_memory_reject(monkeypatch: pytest.MonkeyPatch):
    """Cycle D: explicit edit containing payroll is blocked at write gate."""
    ensure_repo_root_on_path()
    from agent.memory.constants import MEMORY_REJECT_DENYLIST_MESSAGE
    from data.pipelines import rag as rag_mod

    proposal = {
        "location_id": 7,
        "category": "hours",
        "key": "weekend_close",
        "value": "Weekend closing time is 11pm",
    }
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [{"text": "x", "score": 0.5}])
    mock_structured_generation(
        monkeypatch,
        rag_answer="11pm on weekends. Would you like me to remember this for next time?",
        rag_proposal=proposal,
    )

    thread_id = "test-thread-denylist"
    graph_mod.invoke_support_agent(
        "Barranquilla Norte weekend close is 11pm, not 10pm.",
        thread_id=thread_id,
        user_id=12,
    )

    state = graph_mod.invoke_support_agent(
        "Yes, remember it as staff payroll is confidential at this location",
        thread_id=thread_id,
        user_id=12,
    )

    nodes = trace_nodes(state)
    assert "resolve_memory_proposal" in nodes
    assert state["route"] == "memory_reject"
    assert state["answer"] == MEMORY_REJECT_DENYLIST_MESSAGE
    assert state.get("pending_proposal") is None
    assert "memory_ack" not in nodes


def test_memory_ack_template_on_approve_only(monkeypatch: pytest.MonkeyPatch):
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    proposal = {
        "location_id": 4,
        "category": "suppliers",
        "key": "vegetable_delivery_day",
        "value": "Vegetables deliver on Fridays",
    }
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [{"text": "x", "score": 0.5}])
    mock_structured_generation(
        monkeypatch,
        rag_answer="Fridays. Remember?",
        rag_proposal=proposal,
    )

    thread_id = "test-thread-ack-only"
    graph_mod.invoke_support_agent(
        "Chapinero vegetable deliveries are on Fridays, not Thursdays.",
        thread_id=thread_id,
        user_id=3,
    )
    state = graph_mod.invoke_support_agent(
        "Yes, please remember that",
        thread_id=thread_id,
        user_id=3,
    )

    assert state["answer"] == "Got it — I'll remember that for next time."
    assert state["route"] == "memory_ack"


def test_bare_yes_returns_memory_reject_not_kb_refusal(monkeypatch: pytest.MonkeyPatch):
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    proposal = {
        "location_id": 4,
        "category": "suppliers",
        "key": "vegetable_delivery_day",
        "value": "Vegetables deliver on Fridays",
    }
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [{"text": "x", "score": 0.5}])
    mock_structured_generation(
        monkeypatch,
        rag_answer="Fridays. Remember?",
        rag_proposal=proposal,
    )

    thread_id = "test-thread-bare-yes"
    first = graph_mod.invoke_support_agent(
        "Chapinero vegetable deliveries are on Fridays, not Thursdays.",
        thread_id=thread_id,
        user_id=3,
    )
    assert first.get("pending_proposal") is not None

    state = graph_mod.invoke_support_agent("yes", thread_id=thread_id, user_id=3)

    nodes = trace_nodes(state)
    assert "resolve_memory_proposal" in nodes
    assert "memory_reject" in nodes
    assert "refuse" not in nodes
    assert state["route"] == "memory_reject"
    assert "Yes, please remember that" in state["answer"]
    assert state.get("pending_proposal") is None


def test_inferred_proposal_from_confirmation_question(monkeypatch: pytest.MonkeyPatch):
    """LLM asks to update memory but omits memory_proposal JSON — server infers pending."""
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(
        rag_mod,
        "retrieve",
        lambda *_a, **_k: [{"text": "Default Monday delivery.", "score": 0.5}],
    )
    mock_structured_generation(
        monkeypatch,
        rag_answer=(
            "Approved memory for Jacksonville (location_id=14) says Monday. "
            "Would you like me to update the memory to reflect Thursday deliveries?"
        ),
        rag_proposal=None,
    )

    thread_id = "test-thread-inferred-jax"
    first = graph_mod.invoke_support_agent(
        "Jacksonville supplier deliveries are on Thursdays, not Wednesdays.",
        thread_id=thread_id,
        user_id=11,
    )
    assert first.get("pending_proposal") is not None
    assert first["pending_proposal"]["location_id"] == 14
    assert first["pending_proposal"]["key"] == "general_delivery_day"

    state = graph_mod.invoke_support_agent("yes", thread_id=thread_id, user_id=11)
    assert state["route"] == "memory_reject"
    assert "Yes, please remember that" in state["answer"]


def test_bare_yes_without_pending_returns_guidance_not_refusal(monkeypatch: pytest.MonkeyPatch):
    state = graph_mod.invoke_support_agent("yes", thread_id="orphan-bare-yes", user_id=3)
    nodes = {event["node"] for event in state.get("trace_events", [])}
    assert state["route"] == "memory_reject"
    assert "pending memory request" in state["answer"].lower()
    assert "refuse" not in nodes


def test_approve_phrase_after_bare_yes_clears_pending(monkeypatch: pytest.MonkeyPatch):
    """Bare yes clears pending; a later approve phrase should explain how to retry."""
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    proposal = {
        "location_id": 10,
        "category": "suppliers",
        "key": "general_delivery_day",
        "value": "General supplier delivers on Mondays",
    }
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [{"text": "x", "score": 0.5}])
    mock_structured_generation(
        monkeypatch,
        rag_answer="Mondays. Would you like me to remember that?",
        rag_proposal=proposal,
    )

    thread_id = "test-thread-bare-then-approve"
    graph_mod.invoke_support_agent(
        "Fort Lauderdale general supplier deliveries are on Mondays, not Wednesdays.",
        thread_id=thread_id,
        user_id=15,
    )
    graph_mod.invoke_support_agent("yes", thread_id=thread_id, user_id=15)
    state = graph_mod.invoke_support_agent(
        "yes please remember that",
        thread_id=thread_id,
        user_id=15,
    )

    assert state["route"] == "memory_reject"
    assert "don't have a pending memory request to approve" in state["answer"].lower()
    assert "restate" not in state["answer"].lower()


def test_stale_pending_new_correction_runs_propose_turn(monkeypatch: pytest.MonkeyPatch):
    """A new correction while an old pending exists should start a fresh propose turn."""
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    old_proposal = {
        "location_id": 4,
        "category": "suppliers",
        "key": "vegetable_delivery_day",
        "value": "Vegetables deliver on Fridays",
    }
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [{"text": "x", "score": 0.5}])
    mock_structured_generation(
        monkeypatch,
        rag_answer="Fridays. Remember?",
        rag_proposal=old_proposal,
    )

    thread_id = "test-thread-supersede-pending"
    graph_mod.invoke_support_agent(
        "Chapinero vegetable delivery Fridays",
        thread_id=thread_id,
        user_id=21,
    )

    mock_structured_generation(
        monkeypatch,
        rag_answer=(
            "Approved memory for Jacksonville (location_id=14) says Monday. "
            "Would you like me to update the memory to reflect Thursday deliveries?"
        ),
        rag_proposal=None,
    )
    state = graph_mod.invoke_support_agent(
        "Jacksonville supplier deliveries are on Thursdays, not Wednesdays.",
        thread_id=thread_id,
        user_id=21,
    )

    nodes = trace_nodes(state)
    assert "generate" in nodes
    assert "memory_reject" not in nodes
    assert state["route"] == "generate"
    assert state.get("pending_proposal") is not None
    assert state["pending_proposal"]["location_id"] == 14
    assert "remember" in state["answer"].lower() or "update" in state["answer"].lower()
