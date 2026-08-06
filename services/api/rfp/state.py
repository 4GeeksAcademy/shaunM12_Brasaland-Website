"""LangGraph state for RFP intake (context-27 Part 1)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class RfpGraphState(TypedDict, total=False):
    """Minimal explicit state for P1 intake graph."""

    ticket_id: str
    pdf_path: str
    markdown_text: str
    readability_scores: dict[str, Any]
    metadata: dict[str, Any]
    departments_needed: list[str]
    unmapped_topics: list[str]
    department_excerpts: dict[str, str]
    department_key_aspects: dict[str, list[str]]
    conflicts: list[dict[str, Any]]
    intake_summary: str
    requires_ceo_approval: bool
    status: str
    discard_reason: str | None
    error_message: str | None
    error_code: str | None
    trace_events: Annotated[list[dict[str, Any]], operator.add]


def initial_state(*, ticket_id: str, pdf_path: str) -> RfpGraphState:
    return RfpGraphState(
        ticket_id=ticket_id,
        pdf_path=pdf_path,
        markdown_text="",
        readability_scores={},
        metadata={},
        departments_needed=[],
        unmapped_topics=[],
        department_excerpts={},
        department_key_aspects={},
        conflicts=[],
        intake_summary="",
        requires_ceo_approval=False,
        status="analyzing",
        discard_reason=None,
        error_message=None,
        error_code=None,
        trace_events=[],
    )


__all__ = ["RfpGraphState", "initial_state"]
