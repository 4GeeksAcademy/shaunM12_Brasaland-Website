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
    # Part 2 (context-23 P2)
    intent: str
    incident_id: int | None
    incident_filters: dict[str, str]
    sources_used: list[str]
    tool_results: list[dict[str, Any]]


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
        sources_used=[],
        tool_results=[],
    )
