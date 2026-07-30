"""LangGraph state schema for the Support Agent (context-23 Part 1)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict):
    """Minimal Part 1 state — no chat history or Part 2 tool fields."""

    question: str
    chunks: list[dict[str, Any]]
    context_text: str
    answer: str
    route: str
    error: str | None
    trace_events: Annotated[list[dict[str, Any]], operator.add]


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
    )
