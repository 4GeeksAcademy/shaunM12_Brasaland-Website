"""LangGraph state for RFP workflow (context-27 P1 intake + P2 generation)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


def merge_dicts(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
) -> dict[str, Any]:
    """Reducer for parallel department branches (P2 fan-out)."""
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class RfpGraphState(TypedDict, total=False):
    """Explicit state for merged intake + generation graph."""

    ticket_id: str
    pdf_path: str
    invoke_mode: str
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
    # P2 generation (parallel branches merge via reducers)
    active_department_id: str
    department_drafts: Annotated[dict[str, str], merge_dicts]
    department_evaluation_results: Annotated[dict[str, dict[str, Any]], merge_dicts]
    department_draft_statuses: Annotated[dict[str, str], merge_dicts]
    department_failures: Annotated[dict[str, str], merge_dicts]
    # P3 approval (parallel branches merge via reducers)
    department_approval_statuses: Annotated[dict[str, str], merge_dicts]
    arbitration_round: int
    arbitration_resolutions: Annotated[list[dict[str, Any]], operator.add]
    arbitration_exhausted: bool
    ceo_approved: bool
    final_document_markdown: str | None


def initial_state(*, ticket_id: str, pdf_path: str) -> RfpGraphState:
    return RfpGraphState(
        ticket_id=ticket_id,
        pdf_path=pdf_path,
        invoke_mode="intake",
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
        department_drafts={},
        department_evaluation_results={},
        department_draft_statuses={},
        department_failures={},
        department_approval_statuses={},
        arbitration_round=0,
        arbitration_resolutions=[],
        arbitration_exhausted=False,
        ceo_approved=False,
        final_document_markdown=None,
    )


def initial_generation_state(
    *,
    ticket_id: str,
    metadata: dict[str, Any],
    departments_needed: list[str],
    department_key_aspects: dict[str, list[str]],
    department_excerpts: dict[str, str],
    intake_summary: str = "",
    requires_ceo_approval: bool = False,
    conflicts: list[dict[str, Any]] | None = None,
    markdown_text: str = "",
) -> RfpGraphState:
    """Hydrated state for P2-only graph entry (M9-P2-14)."""
    return RfpGraphState(
        ticket_id=ticket_id,
        pdf_path="",
        invoke_mode="generation",
        markdown_text=markdown_text,
        metadata=dict(metadata),
        departments_needed=list(departments_needed),
        department_key_aspects=dict(department_key_aspects),
        department_excerpts=dict(department_excerpts),
        intake_summary=intake_summary,
        requires_ceo_approval=requires_ceo_approval,
        conflicts=list(conflicts or []),
        status="drafting",
        department_drafts={},
        department_evaluation_results={},
        department_draft_statuses={},
        department_failures={},
        trace_events=[],
    )


def initial_approval_state(
    *,
    ticket_id: str,
    metadata: dict[str, Any],
    departments_needed: list[str],
    department_drafts: dict[str, str],
    department_evaluation_results: dict[str, dict[str, Any]],
    department_draft_statuses: dict[str, str],
    department_key_aspects: dict[str, list[str]],
    department_excerpts: dict[str, str],
    intake_summary: str = "",
    requires_ceo_approval: bool = False,
    conflicts: list[dict[str, Any]] | None = None,
    markdown_text: str = "",
    arbitration_resolutions: list[dict[str, Any]] | None = None,
    arbitration_exhausted: bool = False,
) -> RfpGraphState:
    """Hydrated state for P3-only graph entry (M9-P3-3)."""
    return RfpGraphState(
        ticket_id=ticket_id,
        pdf_path="",
        invoke_mode="approval",
        markdown_text=markdown_text,
        metadata=dict(metadata),
        departments_needed=list(departments_needed),
        department_key_aspects=dict(department_key_aspects),
        department_excerpts=dict(department_excerpts),
        department_drafts=dict(department_drafts),
        department_evaluation_results=dict(department_evaluation_results),
        department_draft_statuses=dict(department_draft_statuses),
        intake_summary=intake_summary,
        requires_ceo_approval=requires_ceo_approval,
        conflicts=list(conflicts or []),
        status="waiting_for_approval",
        department_approval_statuses={},
        arbitration_round=0,
        arbitration_resolutions=list(arbitration_resolutions or []),
        arbitration_exhausted=arbitration_exhausted,
        ceo_approved=False,
        final_document_markdown=None,
        trace_events=[],
    )


__all__ = [
    "RfpGraphState",
    "initial_approval_state",
    "initial_generation_state",
    "initial_state",
    "merge_dicts",
]
