"""Shared Support Agent trace assertions (context-25 P25-6)."""

from __future__ import annotations

from typing import Any

import pytest

from agent.memory.schemas import GenerationResult, MemoryProposal


def trace_nodes(state: dict) -> list[str]:
    return [event["node"] for event in state.get("trace_events", [])]


def assert_guardrail_prefix(nodes: list[str]) -> None:
    """Every classified path runs intake → guard_input → memory nodes → classify."""
    assert "intake" in nodes
    assert "guard_input" in nodes
    assert "resolve_memory_proposal" in nodes
    assert "read_memory" in nodes
    assert "classify" in nodes
    ordered = [
        "intake",
        "guard_input",
        "resolve_memory_proposal",
        "read_memory",
        "classify",
    ]
    indices = [nodes.index(name) for name in ordered]
    assert indices == sorted(indices)


def assert_validate_after_generate(nodes: list[str]) -> None:
    """LLM generate paths terminate through validate_output."""
    assert "generate" in nodes
    assert "validate_output" in nodes
    assert nodes.index("generate") < nodes.index("validate_output")


def assert_no_validate_output(nodes: list[str]) -> None:
    assert "validate_output" not in nodes


def structured_generation_result(
    answer: str,
    *,
    proposal: dict[str, Any] | MemoryProposal | None = None,
    proposal_trace: str | None = None,
) -> GenerationResult:
    model = None
    if proposal is not None:
        model = (
            proposal
            if isinstance(proposal, MemoryProposal)
            else MemoryProposal.model_validate(proposal)
        )
    return GenerationResult(
        answer=answer,
        memory_proposal=model,
        proposal_trace=proposal_trace,
    )


def mock_structured_generation(
    monkeypatch: pytest.MonkeyPatch,
    *,
    rag_answer: str | None = None,
    support_answer: str | None = None,
    memory_correction_answer: str | None = None,
    rag_proposal: dict[str, Any] | MemoryProposal | None = None,
    support_proposal: dict[str, Any] | MemoryProposal | None = None,
    memory_correction_proposal: dict[str, Any] | MemoryProposal | None = None,
) -> None:
    """Patch structured generation wrappers used by ``generate_node``."""
    from agent import generation as generation_mod

    def _rag(_question: str, _context: str, **kwargs: Any) -> GenerationResult:
        return structured_generation_result(
            rag_answer or "Structured RAG answer.",
            proposal=rag_proposal,
        )

    def _support(_question: str, **kwargs: Any) -> GenerationResult:
        return structured_generation_result(
            support_answer or "Structured support answer.",
            proposal=support_proposal,
        )

    def _memory_correction(_question: str, **kwargs: Any) -> GenerationResult:
        return structured_generation_result(
            memory_correction_answer or rag_answer or "Structured memory correction answer.",
            proposal=memory_correction_proposal if memory_correction_proposal is not None else rag_proposal,
        )

    monkeypatch.setattr(generation_mod, "generate_structured_rag_response", _rag)
    monkeypatch.setattr(generation_mod, "generate_structured_support_response", _support)
    monkeypatch.setattr(
        generation_mod,
        "generate_structured_memory_correction_response",
        _memory_correction,
    )
