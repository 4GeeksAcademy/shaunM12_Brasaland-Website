"""LangGraph state schema for the Support Agent (context-23 Part 1 + Part 2)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict):
    """Support Agent graph state — P1 fields plus P2 routing/tool fields."""

    question: str
    chunks: list[dict[str, Any]]
    context_text: str
    answer: str
    route: str
    error: str | None
    trace_events: Annotated[list[dict[str, Any]], operator.add]
    # Part 2 (context-23 P2) + P24-3b write path
    intent: str
    incident_id: int | None
    incident_filters: dict[str, str]
    incident_action: str
    write_action: str | None
    write_payload: dict[str, str] | None
    write_status: str | None
    sources_used: list[str]
    tool_results: list[dict[str, Any]]
    redirect_required: bool
    failure_type: str | None
    guardrail_reason: str | None
    personal_use_score: float | None
    fallback_reason: str | None
    # MEM-092 (context-26 P26-L20)
    memory_context: str
    pending_proposal: dict[str, Any] | None
    pending_proposal_at: str | None
    memory_proposal_candidate: dict[str, Any] | None
    last_memory_outcome: str | None
    memory_next: str | None
    memory_notice: str | None


def initial_state(question: str) -> AgentState:
    """Seed state for ``graph.invoke()``."""
    return AgentState(
        question=question,
        chunks=[],
        context_text="",
        answer="",
        route="",
        error=None,
        trace_events=[],
        intent="rag",
        incident_id=None,
        incident_filters={},
        incident_action="list",
        write_action=None,
        write_payload=None,
        write_status=None,
        sources_used=[],
        tool_results=[],
        redirect_required=False,
        failure_type=None,
        guardrail_reason=None,
        personal_use_score=None,
        fallback_reason=None,
        memory_context="",
        pending_proposal=None,
        pending_proposal_at=None,
        memory_proposal_candidate=None,
        last_memory_outcome=None,
        memory_next=None,
        memory_notice=None,
    )
