"""Part 2 routing evals — tool path vs RAG path (P2-L39, P2-L40)."""

from __future__ import annotations

import pytest

from agent import graph as graph_mod
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


def _trace_nodes(state: dict) -> list[str]:
    return [event["node"] for event in state.get("trace_events", [])]


def test_routing_eval_incident_path_skips_retrieve(monkeypatch: pytest.MonkeyPatch):
    """P2-L39: incident question uses live tool path only — never retrieve."""
    retrieve_called = False
    incidents = [
        {
            "id": 55,
            "title": "Slow order complaint",
            "description": "Customer waited over 40 minutes",
            "status": "open",
            "origin": "customer",
            "branch": "miami_doral",
            "category": "customer_complaint",
        },
        {
            "id": 63,
            "title": "Uniform protocol breach",
            "description": "Staff member not in uniform",
            "status": "open",
            "origin": "branch",
            "branch": "miami_doral",
            "category": "staff_issue",
        },
    ]

    def _retrieve(*_a, **_k):
        nonlocal retrieve_called
        retrieve_called = True
        return []

    monkeypatch.setattr(
        "agent.tools.incidents.fetch_json",
        lambda *a, **k: (200, incidents, None),
    )
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(rag_mod, "retrieve", _retrieve)
    import agent.generation as generation_mod

    monkeypatch.setattr(
        generation_mod,
        "generate_support_answer",
        lambda _q, **kwargs: (
            "Open incidents at Miami Doral: #55 Slow order complaint, #63 Uniform protocol breach."
            if kwargs.get("tool_results")
            and len(kwargs["tool_results"][0]["rows"]) == 2
            else "missing tool context"
        ),
    )

    state = graph_mod.invoke_support_agent(
        "List open incidents at Miami Doral",
        auth_header="Bearer routing-eval-token",
    )

    nodes = _trace_nodes(state)
    assert retrieve_called is False
    assert state["intent"] == "incident"
    assert state["route"] == "generate"
    assert nodes.index("classify") < nodes.index("lookup_incident") < nodes.index("generate")
    assert "retrieve" not in nodes
    assert "refuse" not in nodes
    assert state["sources_used"] == ["incidents_api"]
    assert "#55" in state["answer"]
    assert "Slow order" in state["answer"]


def test_routing_eval_rag_path_never_calls_tool_http(monkeypatch: pytest.MonkeyPatch):
    """P2-L40: knowledge-base question uses retrieve path only — never fetch_json."""
    fetch_called = False
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

    def _fetch_json(*_a, **_k):
        nonlocal fetch_called
        fetch_called = True
        return 500, None, "should not be called"

    monkeypatch.setattr("agent.tools.incidents.fetch_json", _fetch_json)
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: chunks)
    monkeypatch.setattr(
        rag_mod,
        "generate_answer",
        lambda _q, _ctx: "Gold tier requires 50 or more loyalty points.",
    )

    state = graph_mod.invoke_support_agent("How many points for Gold tier?")

    nodes = _trace_nodes(state)
    assert fetch_called is False
    assert state["intent"] == "rag"
    assert state["route"] == "generate"
    assert nodes.index("classify") < nodes.index("retrieve") < nodes.index("generate")
    assert "lookup_incident" not in nodes
    assert "lookup_inventory_stock" not in nodes
    assert "fallback" not in nodes
    assert "50" in state["answer"]
    assert state["chunks"] == chunks


def test_routing_eval_incident_unavailable_uses_fallback(monkeypatch: pytest.MonkeyPatch):
    """Optional routing eval #3: incident service unavailable → fallback (no RAG, no generate)."""
    retrieve_called = False
    generate_called = False

    def _retrieve(*_a, **_k):
        nonlocal retrieve_called
        retrieve_called = True
        return []

    def _generate(*_a, **_k):
        nonlocal generate_called
        generate_called = True
        return "made up incidents"

    monkeypatch.setattr(
        "agent.tools.incidents.fetch_json",
        lambda *a, **k: (0, None, "timeout"),
    )
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(rag_mod, "retrieve", _retrieve)
    import agent.generation as generation_mod

    monkeypatch.setattr(generation_mod, "generate_support_answer", _generate)

    state = graph_mod.invoke_support_agent("List open incidents at Miami Doral")

    nodes = _trace_nodes(state)
    assert state["intent"] == "incident"
    assert state["route"] == "fallback"
    assert nodes.index("classify") < nodes.index("lookup_incident") < nodes.index("fallback")
    assert "retrieve" not in nodes
    assert "generate" not in nodes
    assert retrieve_called is False
    assert generate_called is False
    assert "couldn't reach live incident data" in state["answer"].lower()


def test_routing_eval_inventory_path_skips_retrieve(monkeypatch: pytest.MonkeyPatch):
    """P2-L9 stretch: inventory question uses lookup_inventory_stock — never retrieve."""
    retrieve_called = False
    product = {
        "id": 1,
        "name": "Beef brisket",
        "sku": "BRS-BEEF-001",
        "unit": "kg",
        "category": "meat",
        "country": "CO",
        "is_active": True,
        "current_stock": 50.0,
        "min_stock_threshold": 40.0,
    }

    def _retrieve(*_a, **_k):
        nonlocal retrieve_called
        retrieve_called = True
        return []

    monkeypatch.setattr(
        "agent.tools.inventory.fetch_json",
        lambda *a, **k: (200, [product], None),
    )
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(rag_mod, "retrieve", _retrieve)
    import agent.generation as generation_mod

    monkeypatch.setattr(
        generation_mod,
        "generate_support_answer",
        lambda _q, **kwargs: (
            "BRS-BEEF-001 has 50 kg in stock."
            if kwargs.get("tool_results")
            and kwargs["tool_results"][0]["rows"][0]["sku"] == "BRS-BEEF-001"
            else "missing"
        ),
    )

    state = graph_mod.invoke_support_agent(
        "Current stock for SKU BEEF-001",
        auth_header="Bearer routing-eval-token",
    )

    nodes = _trace_nodes(state)
    assert retrieve_called is False
    assert state["intent"] == "inventory"
    assert state["route"] == "generate"
    assert nodes.index("classify") < nodes.index("lookup_inventory_stock") < nodes.index("generate")
    assert "retrieve" not in nodes
    assert "lookup_incident" not in nodes
    assert state["sources_used"] == ["inventory_api"]
    assert "50" in state["answer"]
    assert "BRS-BEEF-001" in state["answer"]
