"""Support Agent LangGraph evals — mocked retrieve/generation (Phase 4 gate)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent import graph as graph_mod
from agent.state import initial_state
from knowledge.bootstrap import ensure_repo_root_on_path
from tests.pipelines.agent_trace_assertions import (
    assert_guardrail_prefix,
    assert_no_validate_output,
    assert_validate_after_generate,
    trace_nodes,
)


@pytest.fixture(autouse=True)
def _agent_env(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Isolated checkpoint DB and RAG env for graph invokes."""
    monkeypatch.setenv("AGENT_CHECKPOINT_DB_PATH", str(tmp_path / "checkpoints.db"))
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "http://embed.test/v1")
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-embed-key")
    monkeypatch.setenv("EMBEDDING_MODEL_ID", "test/embed-model")
    monkeypatch.setenv("GENERATION_BASE_URL", "http://gen.test/v1")
    monkeypatch.setenv("GENERATION_API_KEY", "test-gen-key")
    monkeypatch.setenv("GENERATION_MODEL_ID", "test/chat-model")
    monkeypatch.setenv("RAG_MIN_SCORE", "0.30")
    graph_mod.get_compiled_graph.cache_clear()
    graph_mod._sqlite_checkpointer.cache_clear()
    yield
    graph_mod.get_compiled_graph.cache_clear()
    graph_mod._sqlite_checkpointer.cache_clear()


def test_graph_compiles_with_sqlite_checkpointer(tmp_path):
    graph_mod.get_compiled_graph.cache_clear()
    graph_mod._sqlite_checkpointer.cache_clear()

    compiled = graph_mod.get_compiled_graph()

    assert compiled is not None
    assert (tmp_path / "checkpoints.db").is_file()


def _trace_nodes(state: dict) -> list[str]:
    return trace_nodes(state)


def test_invoke_gold_tier_retrieve_before_generate(monkeypatch: pytest.MonkeyPatch):
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    chunks = [
        {
            "company": "brasaland",
            "source_document": "brasaland-loyalty-program.en.md",
            "section": "Gold tier",
            "language": "en",
            "chunk_index": 0,
            "text": "Gold requires 50+ points.",
            "score": 0.55,
        }
    ]
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: chunks)
    monkeypatch.setattr(
        rag_mod,
        "generate_answer",
        lambda _q, _ctx: "Gold tier requires 50 or more loyalty points.",
    )

    state = graph_mod.invoke_support_agent("How many points for Gold tier?")

    assert state["route"] == "generate"
    assert state["intent"] == "rag"
    assert "50" in state["answer"]
    nodes = _trace_nodes(state)
    assert_guardrail_prefix(nodes)
    assert nodes.index("classify") < nodes.index("retrieve") < nodes.index("generate")
    assert_validate_after_generate(nodes)
    assert "lookup_incident" not in nodes
    assert "refuse" not in nodes
    assert state["chunks"] == chunks


def test_invoke_generation_provider_error_returns_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod
    from openai import PermissionDeniedError

    chunks = [
        {
            "company": "brasaland",
            "source_document": "brasaland-loyalty-program.en.md",
            "section": "Gold tier",
            "language": "en",
            "chunk_index": 0,
            "text": "Gold requires 50+ points.",
            "score": 0.55,
        }
    ]
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: chunks)

    def _raise_provider_block(*_a, **_k):
        raise PermissionDeniedError(
            "Request blocked: prompt injection patterns detected",
            response=MagicMock(request=MagicMock()),
            body=None,
        )

    monkeypatch.setattr(rag_mod, "generate_answer", _raise_provider_block)

    state = graph_mod.invoke_support_agent("How many points for Gold tier?")

    assert state["route"] == "fallback"
    assert state["fallback_reason"] == "generation_provider_error"
    assert "answer service" in state["answer"].lower()
    nodes = _trace_nodes(state)
    assert "generate" in nodes
    assert_validate_after_generate(nodes)


def test_invoke_whitespace_skips_retrieve(monkeypatch: pytest.MonkeyPatch):
    retrieve_called = False

    def _retrieve(*_a, **_k):
        nonlocal retrieve_called
        retrieve_called = True
        return []

    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(rag_mod, "retrieve", _retrieve)

    state = graph_mod.invoke_support_agent("   ")

    assert retrieve_called is False
    assert state["route"] == "error"
    nodes = _trace_nodes(state)
    assert "guard_input" not in nodes
    assert "retrieve" not in nodes
    assert "classify" not in nodes
    assert "intake" in nodes


def test_invoke_empty_retrieval_refuses_without_generate(
    monkeypatch: pytest.MonkeyPatch,
):
    generate_called = False

    def _generate(*_a, **_k):
        nonlocal generate_called
        generate_called = True
        return "should not run"

    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [])
    monkeypatch.setattr(rag_mod, "generate_answer", _generate)

    state = graph_mod.invoke_support_agent("What is the secret menu?")

    assert generate_called is False
    assert state["route"] == "refuse"
    nodes = _trace_nodes(state)
    assert_guardrail_prefix(nodes)
    assert nodes.index("classify") < nodes.index("retrieve")
    assert "refuse" in nodes
    assert "generate" not in nodes
    assert_no_validate_output(nodes)
    assert "don't have enough information" in state["answer"].lower()


def test_resolve_procedure_hint_for_incident_create():
    from agent.fallbacks import resolve_procedure_hint

    hint = resolve_procedure_hint("How do I create an incident")
    assert hint is not None
    assert "Create incident for" in hint

    hint_you = resolve_procedure_hint("how do you create an incident?")
    assert hint_you is not None
    assert "Create incident for" in hint_you


def test_invoke_procedure_incident_create_returns_hint(monkeypatch: pytest.MonkeyPatch):
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [])

    state = graph_mod.invoke_support_agent("How do I create an incident")

    assert state["intent"] == "rag"
    assert state["route"] == "refuse"
    assert "Create incident for" in state["answer"]
    assert "don't have enough information" not in state["answer"].lower()


def test_invoke_how_do_you_create_incident_returns_hint(monkeypatch: pytest.MonkeyPatch):
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    mcp_called = False

    def _mcp_lookup(**_k):
        nonlocal mcp_called
        mcp_called = True
        return {"ok": False, "rows": []}

    monkeypatch.setattr("agent.graph.lookup_incidents_via_mcp", _mcp_lookup)
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [])

    state = graph_mod.invoke_support_agent("how do you create an incident?")

    assert mcp_called is False
    assert state["intent"] == "rag"
    assert state["route"] == "refuse"
    assert "lookup_incident" not in _trace_nodes(state)
    assert "Create incident for" in state["answer"]


def test_invoke_show_all_incidents_skips_retrieve(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "agent.graph.lookup_incidents_via_mcp",
        lambda **k: {
            "source": "incidents_api",
            "ok": True,
            "http_status": 200,
            "filters": {},
            "rows": [{"id": 1, "title": "Test", "status": "open", "branch": "miami_doral"}],
            "error": None,
            "reason": None,
        },
    )
    ensure_repo_root_on_path()
    import agent.generation as generation_mod

    monkeypatch.setattr(
        generation_mod,
        "generate_support_answer",
        lambda _q, **kwargs: "Incident list answer",
    )

    state = graph_mod.invoke_support_agent("show me all incidents")

    assert state["intent"] == "incident"
    nodes = _trace_nodes(state)
    assert_guardrail_prefix(nodes)
    assert "lookup_incident" in nodes
    assert "retrieve" not in nodes
    assert state["route"] == "generate"
    assert_validate_after_generate(nodes)


def test_resolve_ops_misroute_hint_for_incident_phrasing():
    from agent.fallbacks import resolve_ops_misroute_hint

    hint = resolve_ops_misroute_hint("show me all incidents")
    assert hint is not None
    assert "List open incidents" in hint


def test_resolve_ops_misroute_hint_skips_kb_questions():
    from agent.fallbacks import resolve_ops_misroute_hint

    assert resolve_ops_misroute_hint("How many points for Gold tier?") is None


def test_initial_state_seeds_required_keys():
    state = initial_state("loyalty points")

    assert state["question"] == "loyalty points"
    assert state["chunks"] == []
    assert state["trace_events"] == []
    assert state["intent"] == "rag"
    assert state["redirect_required"] is False
    assert state["failure_type"] is None
    assert state["guardrail_reason"] is None
    assert state["personal_use_score"] is None
    assert state["fallback_reason"] is None
    assert state["incident_id"] is None
    assert state["incident_filters"] == {}
    assert state["incident_action"] == "list"
    assert state["write_action"] is None
    assert state["tool_results"] == []


def test_invoke_incident_path_skips_retrieve(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "agent.graph.lookup_incidents_via_mcp",
        lambda **k: {
            "source": "incidents_api",
            "ok": True,
            "http_status": 200,
            "filters": {},
            "rows": [],
            "error": None,
            "reason": "empty",
        },
    )

    state = graph_mod.invoke_support_agent("List open incidents at Miami Doral")

    nodes = _trace_nodes(state)
    assert state["intent"] == "incident"
    assert "classify" in nodes
    assert "lookup_incident" in nodes
    assert "retrieve" not in nodes
    assert state["route"] == "fallback"


def test_invoke_incident_with_rows_generates(monkeypatch: pytest.MonkeyPatch):
    incident = {
        "id": 1,
        "title": "Oven fault",
        "description": "Main oven not heating",
        "status": "open",
        "origin": "branch",
        "branch": "miami_doral",
        "category": "equipment_failure",
    }
    monkeypatch.setattr(
        "agent.graph.lookup_incidents_via_mcp",
        lambda **k: {
            "source": "incidents_api",
            "ok": True,
            "http_status": 200,
            "filters": {},
            "rows": [incident],
            "error": None,
            "reason": None,
        },
    )
    ensure_repo_root_on_path()
    import agent.generation as generation_mod

    monkeypatch.setattr(
        generation_mod,
        "generate_support_answer",
        lambda _q, **kwargs: (
            "Oven fault"
            if kwargs.get("tool_results")
            and kwargs["tool_results"][0]["rows"][0]["title"] == "Oven fault"
            else "missing"
        ),
    )

    state = graph_mod.invoke_support_agent(
        "List open incidents at Miami Doral",
        auth_header="Bearer test-token",
    )

    nodes = _trace_nodes(state)
    assert_guardrail_prefix(nodes)
    assert state["route"] == "generate"
    assert "lookup_incident" in nodes
    assert "retrieve" not in nodes
    assert_validate_after_generate(nodes)
    assert state["sources_used"] == ["incidents_api"]
    assert "Oven fault" in state["answer"]


def test_invoke_both_path_uses_generate_support_answer(monkeypatch: pytest.MonkeyPatch):
    incident = {
        "id": 9,
        "title": "Delivery delay",
        "description": "Late shipment",
        "status": "open",
        "origin": "branch",
        "branch": "miami_doral",
        "category": "delivery_issue",
    }
    chunks = [
        {
            "source_document": "waste-policy.md",
            "section": "Disposal",
            "text": "Food waste must be logged daily.",
            "score": 0.55,
        }
    ]
    support_called = False

    def _support(_q, **kwargs):
        nonlocal support_called
        support_called = True
        assert kwargs.get("tool_results")
        assert kwargs.get("rag_context")
        return "Combined incidents and waste policy answer."

    monkeypatch.setattr(
        "agent.graph.lookup_incidents_via_mcp",
        lambda **k: {
            "source": "incidents_api",
            "ok": True,
            "http_status": 200,
            "filters": {},
            "rows": [incident],
            "error": None,
            "reason": None,
        },
    )
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: chunks)
    import agent.generation as generation_mod

    monkeypatch.setattr(generation_mod, "generate_support_answer", _support)

    state = graph_mod.invoke_support_agent(
        "Open incidents at Miami Doral and our waste disposal policy",
    )

    nodes = _trace_nodes(state)
    assert_guardrail_prefix(nodes)
    assert state["intent"] == "both"
    assert support_called is True
    assert "lookup_incident" in nodes
    assert "retrieve" in nodes
    assert "generate" in nodes
    assert_validate_after_generate(nodes)
    assert state["route"] == "generate"
    assert "Combined" in state["answer"]


def test_graph_nodes_never_call_monolithic_query(monkeypatch: pytest.MonkeyPatch):
    """P1-L3: retrieve/generate nodes must not delegate to rag.query()."""
    query_called = False

    def _query(*_a, **_k):
        nonlocal query_called
        query_called = True
        return "monolithic path"

    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    chunks = [
        {
            "source_document": "brasaland-loyalty-program.en.md",
            "section": "Gold tier",
            "text": "Gold requires 50+ points.",
            "score": 0.50,
        }
    ]
    monkeypatch.setattr(rag_mod, "query", _query)
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: chunks)
    monkeypatch.setattr(
        rag_mod,
        "generate_answer",
        lambda _q, _ctx: "Gold needs 50+ points.",
    )

    state = graph_mod.invoke_support_agent("How many points for Gold tier?")

    assert query_called is False
    assert state["route"] == "generate"
    nodes = _trace_nodes(state)
    assert_guardrail_prefix(nodes)
    assert_validate_after_generate(nodes)
    assert len(state["trace_events"]) >= 6
