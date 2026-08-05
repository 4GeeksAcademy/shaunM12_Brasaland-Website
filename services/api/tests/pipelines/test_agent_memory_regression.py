"""P26-6 merge gate — memory module regression and boundary checks."""

from __future__ import annotations

import inspect

import pytest

from agent import graph as graph_mod
from agent.schemas import AgentQueryRequest, AgentQueryResponse
from agent.state import initial_state
from knowledge.bootstrap import ensure_repo_root_on_path
from tests.pipelines.agent_trace_assertions import (
    assert_guardrail_prefix,
    assert_validate_after_generate,
    mock_structured_generation,
    trace_nodes,
)


@pytest.fixture(autouse=True)
def _agent_regression_env(monkeypatch: pytest.MonkeyPatch, tmp_path):
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


def test_support_agent_trace_includes_memory_nodes(monkeypatch: pytest.MonkeyPatch):
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(
        rag_mod,
        "retrieve",
        lambda *_a, **_k: [{"text": "Gold requires 50+ points.", "score": 0.55}],
    )
    mock_structured_generation(
        monkeypatch,
        rag_answer="Gold tier requires 50 or more loyalty points.",
    )

    state = graph_mod.invoke_support_agent("How many points for Gold tier?", user_id=1)
    nodes = trace_nodes(state)

    assert_guardrail_prefix(nodes)
    assert nodes.index("read_memory") < nodes.index("classify")
    assert_validate_after_generate(nodes)


def test_memory_graph_nodes_registered():
    graph = graph_mod.build_graph()
    node_names = set(graph.nodes.keys())
    assert {"resolve_memory_proposal", "read_memory", "memory_ack", "memory_reject"}.issubset(
        node_names
    )


def test_initial_state_memory_fields_present():
    state = initial_state("loyalty tier question")
    assert "memory_context" in state
    assert "pending_proposal" in state
    assert "memory_proposal_candidate" in state


def test_agent_query_request_accepts_optional_thread_id():
    body = AgentQueryRequest(question="List open incidents", thread_id="thread-123")
    assert body.thread_id == "thread-123"


def test_agent_query_response_is_answer_only():
    fields = AgentQueryResponse.model_fields
    assert set(fields.keys()) == {"answer"}


def test_knowledge_generate_answer_signature_unchanged():
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    signature = inspect.signature(rag_mod.generate_answer)
    assert list(signature.parameters.keys()) == ["question", "context"]
    assert signature.return_annotation in (str, "str", inspect.Signature.empty)


def test_invoke_support_agent_accepts_user_id_and_thread_id(monkeypatch: pytest.MonkeyPatch):
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: [])

    state = graph_mod.invoke_support_agent(
        "What is the secret menu?",
        thread_id="regression-thread",
        user_id=99,
    )

    assert state["route"] == "refuse"
