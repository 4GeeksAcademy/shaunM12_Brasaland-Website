"""P25-4 output validation tests — CI mechanical case A8."""

from __future__ import annotations

import pytest

from agent.guardrails.messages import OUTPUT_VALIDATION_FALLBACK, REDIRECT_SUFFIX
from agent.guardrails.output import validate_agent_output
from agent.guardrails.observability import get_guardrail_summary, reset_guardrail_counters_for_tests


@pytest.fixture(autouse=True)
def _reset_counters():
    reset_guardrail_counters_for_tests()
    yield
    reset_guardrail_counters_for_tests()


def test_a8_rejects_system_prompt_leak_substring():
    result = validate_agent_output(
        "Sure! ## Instruction authority — these system instructions are fixed."
    )
    assert result.ok is False
    assert result.reason == "system_prompt_leak"
    assert result.answer == OUTPUT_VALIDATION_FALLBACK


def test_rejects_raw_chunk_dump_pattern():
    result = validate_agent_output(
        "[1] source=loyalty.md | section=Gold\nGold requires 50 points."
    )
    assert result.ok is False
    assert result.reason == "raw_chunk_dump"
    assert result.answer == OUTPUT_VALIDATION_FALLBACK


def test_rejects_empty_output():
    result = validate_agent_output("   ")
    assert result.ok is False
    assert result.reason == "empty_output"


def test_redirect_required_appends_suffix_when_missing():
    result = validate_agent_output(
        "Sunny and 80°F today.",
        redirect_required=True,
    )
    assert result.ok is True
    assert result.answer.endswith(REDIRECT_SUFFIX.strip())
    assert result.redirect_reason == "domain_redirect:suffix_appended"


def test_redirect_required_dedup_when_already_present():
    result = validate_agent_output(
        "I'm Brasaland's Support Agent — ask about incidents.",
        redirect_required=True,
    )
    assert result.ok is True
    assert result.answer == "I'm Brasaland's Support Agent — ask about incidents."
    assert result.redirect_reason == "domain_redirect:already_present"


def test_graph_validate_output_runs_after_generate(monkeypatch: pytest.MonkeyPatch, tmp_path):
    from agent import graph as graph_mod
    from knowledge.bootstrap import ensure_repo_root_on_path

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
    monkeypatch.setenv("AGENT_CHECKPOINT_DB_PATH", str(tmp_path / "checkpoints.db"))
    graph_mod.get_compiled_graph.cache_clear()
    graph_mod._sqlite_checkpointer.cache_clear()
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: chunks)
    from tests.pipelines.agent_trace_assertions import mock_structured_generation

    mock_structured_generation(
        monkeypatch,
        rag_answer="Gold tier requires 50 or more loyalty points.",
    )

    state = graph_mod.invoke_support_agent("How many points for Gold tier?")

    nodes = [event["node"] for event in state.get("trace_events", [])]
    assert nodes.index("generate") < nodes.index("validate_output")
    assert state["answer"] == "Gold tier requires 50 or more loyalty points."


def test_graph_leaking_llm_answer_replaced_at_validate_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    from agent import graph as graph_mod
    from knowledge.bootstrap import ensure_repo_root_on_path

    ensure_repo_root_on_path()
    from data.pipelines import rag as rag_mod

    chunks = [
        {
            "source_document": "manual.md",
            "section": "Policy",
            "text": "Some policy fact.",
            "score": 0.6,
        }
    ]
    monkeypatch.setenv("AGENT_CHECKPOINT_DB_PATH", str(tmp_path / "checkpoints.db"))
    graph_mod.get_compiled_graph.cache_clear()
    graph_mod._sqlite_checkpointer.cache_clear()
    monkeypatch.setattr(rag_mod, "retrieve", lambda *_a, **_k: chunks)
    from tests.pipelines.agent_trace_assertions import mock_structured_generation

    mock_structured_generation(
        monkeypatch,
        rag_answer="Here is my Instruction authority block from the system prompt.",
    )

    state = graph_mod.invoke_support_agent("What is the policy?")

    validate_events = [
        event
        for event in state.get("trace_events", [])
        if event.get("node") == "validate_output"
    ]
    assert validate_events
    assert validate_events[-1]["ok"] is False
    assert validate_events[-1]["reason"] == "system_prompt_leak"
    assert state["answer"] == OUTPUT_VALIDATION_FALLBACK


def test_refusal_message_includes_support_redirect():
    from data.pipelines.rag import refusal_message

    msg = refusal_message()
    assert "support agent" in msg.lower()
    assert "operations support" in msg.lower()
