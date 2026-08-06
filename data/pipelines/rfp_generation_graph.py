"""RFP Part 2 LangGraph — parallel department generation + evaluation (context-27 P2).

Merged into the compiled RFP graph via ``add_generation_nodes`` (M9-P2-1).
P2-only invoke uses ``invoke_mode="generation"`` entry at ``draft_start`` (M9-P2-14).
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.graph import END
from langgraph.types import Send

from data.pipelines.rfp_intake import _ensure_repo_root_on_path
from data.pipelines.rfp_trace import trace_node

_ensure_repo_root_on_path()

from rfp.constants import (  # noqa: E402
    ERROR_PIPELINE_ERROR,
    STATUS_DRAFTING,
    STATUS_FAILED,
    STATUS_WAITING_FOR_APPROVAL,
    TERMINAL_DRAFT_STATUSES,
)
from rfp.state import RfpGraphState  # noqa: E402

logger = logging.getLogger(__name__)


def _load_generation():
    from data.pipelines import rfp_generation as generation

    return generation


def _draft_start_node(state: RfpGraphState) -> dict[str, Any]:
    """Initialize P2 — set ticket drafting (M9-P2-M6).

    Per-section ``pending`` is set in Postgres by ``prepare_draft_start``; graph state
    only records statuses once a department branch completes.
    """
    departments = list(state.get("departments_needed") or [])
    return {
        "status": STATUS_DRAFTING,
        "trace_events": trace_node(
            "draft_start",
            input_data={"departments_needed": departments},
            output_data={"department_count": len(departments)},
        ),
    }


def _incomplete_departments(state: RfpGraphState) -> list[str]:
    """Departments without a persisted draft and terminal draft_status."""
    departments = list(state.get("departments_needed") or [])
    drafts = state.get("department_drafts") or {}
    statuses = state.get("department_draft_statuses") or {}
    incomplete: list[str] = []
    for dept in departments:
        draft = (drafts.get(dept) or "").strip()
        status = statuses.get(dept)
        if not draft or status not in TERMINAL_DRAFT_STATUSES:
            incomplete.append(dept)
    return incomplete


def _route_after_draft_start(
    state: RfpGraphState,
) -> list[Send] | Literal["generation_finalize"]:
    """Parallel fan-out per department, or skip to finalize on empty."""
    departments = list(state.get("departments_needed") or [])
    if not departments:
        return "generation_finalize"
    sends: list[Send] = []
    for dept in departments:
        sends.append(
            Send(
                "generate_eval_dept",
                {
                    "active_department_id": dept,
                    "ticket_id": state.get("ticket_id"),
                    "metadata": state.get("metadata") or {},
                    "department_key_aspects": state.get("department_key_aspects") or {},
                    "department_excerpts": state.get("department_excerpts") or {},
                    "intake_summary": state.get("intake_summary") or "",
                },
            )
        )
    return sends


def _generate_eval_dept_node(state: RfpGraphState) -> dict[str, Any]:
    """Run generate → eval loop for one department branch."""
    generation = _load_generation()
    dept = state.get("active_department_id")
    if not dept:
        return {}

    metadata = state.get("metadata") or {}
    key_aspects = list((state.get("department_key_aspects") or {}).get(dept) or [])
    excerpt = (state.get("department_excerpts") or {}).get(dept, "")
    intake_summary = state.get("intake_summary") or ""

    try:
        draft, evaluation_results, draft_status = generation.run_department_generation_loop(
            department_id=dept,
            metadata=metadata,
            key_aspects=key_aspects,
            excerpt=excerpt,
            intake_summary=intake_summary,
            use_llm_relevance=False,
        )
    except generation.GenerationUnavailableError as exc:
        logger.exception("Generation unavailable for dept %s", dept)
        return {
            "department_failures": {dept: str(exc)},
            "trace_events": trace_node(
                "generate_eval_dept",
                input_data={"department_id": dept},
                output_data={"ok": False, "error": str(exc)},
            ),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Department generation failed for %s", dept)
        return {
            "department_failures": {dept: str(exc)},
            "trace_events": trace_node(
                "generate_eval_dept",
                input_data={"department_id": dept},
                output_data={"ok": False, "error": str(exc)},
            ),
        }

    return {
        "department_drafts": {dept: draft},
        "department_evaluation_results": {dept: evaluation_results},
        "department_draft_statuses": {dept: draft_status},
        "trace_events": trace_node(
            "generate_eval_dept",
            input_data={"department_id": dept},
            output_data={
                "draft_status": draft_status,
                "overall_passed": evaluation_results.get("latest", {}).get("overall_passed"),
                "iteration": evaluation_results.get("latest", {}).get("iteration"),
            },
        ),
    }


def _generation_finalize_node(state: RfpGraphState) -> dict[str, Any]:
    """Set P2 terminal ticket status when all department branches complete."""
    failures = state.get("department_failures") or {}
    if failures:
        first_error = next(iter(failures.values()))
        return {
            "status": STATUS_FAILED,
            "error_code": ERROR_PIPELINE_ERROR,
            "error_message": first_error,
            "trace_events": trace_node(
                "generation_finalize",
                input_data={"department_failures": list(failures.keys())},
                output_data={"ok": False, "status": STATUS_FAILED, "error": first_error},
            ),
        }

    incomplete = _incomplete_departments(state)
    if incomplete:
        message = (
            "Draft generation incomplete — missing or non-terminal sections: "
            + ", ".join(incomplete)
        )
        logger.error(message)
        return {
            "status": STATUS_FAILED,
            "error_code": ERROR_PIPELINE_ERROR,
            "error_message": message,
            "trace_events": trace_node(
                "generation_finalize",
                input_data={"incomplete_departments": incomplete},
                output_data={"ok": False, "status": STATUS_FAILED, "error": message},
            ),
        }

    statuses = state.get("department_draft_statuses") or {}
    return {
        "status": STATUS_WAITING_FOR_APPROVAL,
        "trace_events": trace_node(
            "generation_finalize",
            input_data={"department_count": len(statuses)},
            output_data={"status": STATUS_WAITING_FOR_APPROVAL, "department_statuses": statuses},
        ),
    }


def _route_entry(state: RfpGraphState) -> Literal["convert_pdf", "draft_start", "approval_start"]:
    mode = state.get("invoke_mode")
    if mode == "generation":
        return "draft_start"
    if mode == "approval":
        return "approval_start"
    return "convert_pdf"


def add_generation_nodes(builder) -> None:
    """Attach P2 nodes and edges to the shared RFP StateGraph builder."""
    builder.add_node("draft_start", _draft_start_node)
    builder.add_node("generate_eval_dept", _generate_eval_dept_node)
    builder.add_node("generation_finalize", _generation_finalize_node)

    builder.add_conditional_edges(
        "draft_start",
        _route_after_draft_start,
        ["generate_eval_dept", "generation_finalize"],
    )
    builder.add_edge("generate_eval_dept", "generation_finalize")
    builder.add_edge("generation_finalize", END)


def set_entry_router(builder) -> None:
    """Route intake vs generation invoke modes (M9-P2-14)."""
    builder.set_conditional_entry_point(
        _route_entry,
        {
            "convert_pdf": "convert_pdf",
            "draft_start": "draft_start",
            "approval_start": "approval_start",
        },
    )


__all__ = [
    "add_generation_nodes",
    "set_entry_router",
]
