"""Part 2 routing evals — tool path vs RAG path (P2-L39, P2-L40)."""

from __future__ import annotations

import pytest

from agent import graph as graph_mod
from knowledge.bootstrap import ensure_repo_root_on_path
from tests.pipelines.agent_trace_assertions import (
    assert_guardrail_prefix,
    assert_no_validate_output,
    assert_validate_after_generate,
    mock_structured_generation,
    structured_generation_result,
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


def _incidents_envelope(rows: list[dict], *, ok: bool = True, reason: str | None = None) -> dict:
    return {
        "source": "incidents_api",
        "ok": ok,
        "http_status": 200 if ok else 0,
        "filters": {},
        "rows": rows if ok else [],
        "error": None if ok else reason,
        "reason": reason,
    }


def _trace_nodes(state: dict) -> list[str]:
    return trace_nodes(state)


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
        "agent.graph.lookup_incidents_via_mcp",
        lambda **k: _incidents_envelope(incidents),
    )
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(rag_mod, "retrieve", _retrieve)
    import agent.generation as generation_mod

    def _support(_q, **kwargs):
        return structured_generation_result(
            "Open incidents at Miami Doral: #55 Slow order complaint, #63 Uniform protocol breach."
            if kwargs.get("tool_results")
            and len(kwargs["tool_results"][0]["rows"]) == 2
            else "missing tool context"
        )

    monkeypatch.setattr(generation_mod, "generate_structured_support_response", _support)

    state = graph_mod.invoke_support_agent(
        "List open incidents at Miami Doral",
        auth_header="Bearer routing-eval-token",
    )

    nodes = _trace_nodes(state)
    assert retrieve_called is False
    assert_guardrail_prefix(nodes)
    assert state["intent"] == "incident"
    assert state["route"] == "generate"
    assert nodes.index("classify") < nodes.index("lookup_incident") < nodes.index("generate")
    assert_validate_after_generate(nodes)
    assert "retrieve" not in nodes
    assert "refuse" not in nodes
    assert state["sources_used"] == ["incidents_api"]
    assert "#55" in state["answer"]
    assert "Slow order" in state["answer"]


def test_routing_eval_rag_path_never_calls_tool_http(monkeypatch: pytest.MonkeyPatch):
    """P2-L40: knowledge-base question uses retrieve path only — never MCP incident lookup."""
    mcp_called = False
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

    def _mcp_lookup(**_k):
        nonlocal mcp_called
        mcp_called = True
        return _incidents_envelope([], ok=False, reason="should not be called")

    monkeypatch.setattr("agent.graph.lookup_incidents_via_mcp", _mcp_lookup)
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: chunks)
    mock_structured_generation(
        monkeypatch,
        rag_answer="Gold tier requires 50 or more loyalty points.",
    )

    state = graph_mod.invoke_support_agent("How many points for Gold tier?")

    nodes = _trace_nodes(state)
    assert mcp_called is False
    assert_guardrail_prefix(nodes)
    assert state["intent"] == "rag"
    assert state["route"] == "generate"
    assert nodes.index("classify") < nodes.index("retrieve") < nodes.index("generate")
    assert_validate_after_generate(nodes)
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
        return structured_generation_result("made up incidents")

    monkeypatch.setattr(
        "agent.graph.lookup_incidents_via_mcp",
        lambda **k: _incidents_envelope([], ok=False, reason="timeout"),
    )
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod
    import agent.generation as generation_mod

    monkeypatch.setattr(rag_mod, "retrieve", _retrieve)
    monkeypatch.setattr(generation_mod, "generate_structured_support_response", _generate)

    state = graph_mod.invoke_support_agent("List open incidents at Miami Doral")

    nodes = _trace_nodes(state)
    assert_guardrail_prefix(nodes)
    assert state["intent"] == "incident"
    assert state["route"] == "fallback"
    assert nodes.index("classify") < nodes.index("lookup_incident") < nodes.index("fallback")
    assert_no_validate_output(nodes)
    assert "retrieve" not in nodes
    assert "generate" not in nodes
    assert retrieve_called is False
    assert generate_called is False
    assert "couldn't reach live incident data" in state["answer"].lower()


def test_routing_eval_incident_write_uses_template_confirmation(
    monkeypatch: pytest.MonkeyPatch,
):
    """P24-3b: write path uses mutate_incident + confirm_write — no LLM generate."""
    generate_called = False
    created = {
        "id": 101,
        "title": "Broken POS",
        "description": "Terminal frozen",
        "status": "open",
        "origin": "branch",
        "branch": "miami_doral",
        "category": "pos_system",
    }

    def _generate(*_a, **_k):
        nonlocal generate_called
        generate_called = True
        return structured_generation_result("LLM should not run")

    monkeypatch.setattr(
        "agent.graph.mutate_incident_via_mcp",
        lambda **k: _incidents_envelope([created], ok=True)
        | {"action": "create"},
    )
    ensure_repo_root_on_path()
    import agent.generation as generation_mod

    monkeypatch.setattr(generation_mod, "generate_structured_support_response", _generate)

    state = graph_mod.invoke_support_agent(
        "Create incident for broken POS at Miami Doral: terminal frozen during lunch rush",
        auth_header="Bearer routing-eval-token",
    )

    nodes = _trace_nodes(state)
    assert_guardrail_prefix(nodes)
    assert state["intent"] == "incident_write"
    assert state["route"] == "confirm_write"
    assert nodes.index("classify") < nodes.index("mutate_incident") < nodes.index("confirm_write")
    assert_no_validate_output(nodes)
    assert "generate" not in nodes
    assert generate_called is False
    assert "Incident #101 created successfully" in state["answer"]


def test_routing_eval_incident_summary_skips_retrieve(monkeypatch: pytest.MonkeyPatch):
    """P24-OPT-G1: summary questions use lookup_incident with summary action."""
    retrieve_called = False
    summary = {
        "by_status": {"open": 3},
        "by_category": {"customer_complaint": 2},
        "by_origin": {"customer": 3},
        "by_branch": {"miami_doral": 3},
    }

    def _retrieve(*_a, **_k):
        nonlocal retrieve_called
        retrieve_called = True
        return []

    monkeypatch.setattr(
        "agent.graph.lookup_incidents_via_mcp",
        lambda **k: {
            "source": "incidents_api",
            "ok": True,
            "http_status": 200,
            "filters": {},
            "rows": [],
            "summary": summary,
            "action": "summary",
            "error": None,
            "reason": None,
        },
    )
    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    monkeypatch.setattr(rag_mod, "retrieve", _retrieve)
    import agent.generation as generation_mod

    def _support(_q, **kwargs):
        return structured_generation_result(
            "3 open incidents"
            if kwargs.get("tool_results") and kwargs["tool_results"][0].get("summary")
            else "missing"
        )

    monkeypatch.setattr(generation_mod, "generate_structured_support_response", _support)

    state = graph_mod.invoke_support_agent("How many open incidents are there?")

    nodes = _trace_nodes(state)
    assert retrieve_called is False
    assert_guardrail_prefix(nodes)
    assert state["intent"] == "incident"
    assert state["route"] == "generate"
    assert "lookup_incident" in nodes
    assert_validate_after_generate(nodes)
    assert "3 open incidents" in state["answer"]


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

    def _support(_q, **kwargs):
        return structured_generation_result(
            "BRS-BEEF-001 has 50 kg in stock."
            if kwargs.get("tool_results")
            and kwargs["tool_results"][0]["rows"][0]["sku"] == "BRS-BEEF-001"
            else "missing"
        )

    monkeypatch.setattr(generation_mod, "generate_structured_support_response", _support)

    state = graph_mod.invoke_support_agent(
        "Current stock for SKU BEEF-001",
        auth_header="Bearer routing-eval-token",
    )

    nodes = _trace_nodes(state)
    assert retrieve_called is False
    assert_guardrail_prefix(nodes)
    assert state["intent"] == "inventory"
    assert state["route"] == "generate"
    assert nodes.index("classify") < nodes.index("lookup_inventory_stock") < nodes.index("generate")
    assert_validate_after_generate(nodes)
    assert "retrieve" not in nodes
    assert "lookup_incident" not in nodes
    assert state["sources_used"] == ["inventory_api"]
    assert "50" in state["answer"]
    assert "BRS-BEEF-001" in state["answer"]


def test_routing_eval_inventory_write_blocks_without_http(
    monkeypatch: pytest.MonkeyPatch,
):
    fetch_called = False

    def _fetch(*_a, **_k):
        nonlocal fetch_called
        fetch_called = True
        return 200, [], None

    monkeypatch.setattr("agent.tools.inventory.fetch_json", _fetch)

    state = graph_mod.invoke_support_agent("Restock SKU BEEF-001 at location 1")

    nodes = _trace_nodes(state)
    assert fetch_called is False
    assert_guardrail_prefix(nodes)
    assert state["intent"] == "inventory_write"
    assert state["route"] == "fallback"
    assert "inventory_write_block" in nodes
    assert_no_validate_output(nodes)
    assert "lookup_inventory_stock" not in nodes
    assert "only read inventory" in state["answer"].lower()


def test_routing_eval_vague_inventory_query_fallback(monkeypatch: pytest.MonkeyPatch):
    state = graph_mod.invoke_support_agent("Show me inventory levels")

    assert state["intent"] == "inventory"
    assert state["route"] == "fallback"
    assert "SKU" in state["answer"] or "product" in state["answer"].lower()
