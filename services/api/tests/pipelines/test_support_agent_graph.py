"""Support Agent LangGraph evals — mocked retrieve/generation (Phase 4 gate)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent import graph as graph_mod
from agent.state import initial_state
from knowledge.bootstrap import ensure_repo_root_on_path


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
    return [event["node"] for event in state.get("trace_events", [])]


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
    assert "50" in state["answer"]
    nodes = _trace_nodes(state)
    assert nodes.index("retrieve") < nodes.index("generate")
    assert "refuse" not in nodes
    assert state["chunks"] == chunks


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
    assert "retrieve" not in _trace_nodes(state)
    assert "intake" in _trace_nodes(state)


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
    assert "retrieve" in nodes
    assert "refuse" in nodes
    assert "generate" not in nodes
    assert "don't have enough information" in state["answer"].lower()


def test_initial_state_seeds_required_keys():
    state = initial_state("loyalty points")

    assert state["question"] == "loyalty points"
    assert state["chunks"] == []
    assert state["trace_events"] == []


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
    assert len(state["trace_events"]) >= 3
