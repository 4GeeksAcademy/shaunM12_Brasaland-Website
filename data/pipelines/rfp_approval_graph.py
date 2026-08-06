"""RFP Part 3 LangGraph — parallel department approval + arbitration + synthesis (context-27 P3).

Merged into the compiled RFP graph via ``add_approval_nodes`` (M9-P2-1 pattern).
P3-only invoke uses ``invoke_mode="approval"`` entry at ``approval_start``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from langgraph.graph import END
from langgraph.types import Send, interrupt

from data.pipelines.rfp_intake import _ensure_repo_root_on_path

_ensure_repo_root_on_path()

from data.pipelines.rfp_approval_packet import (  # noqa: E402
    ApprovalResponseError,
    build_ceo_approval_packet,
    build_dept_approval_packet,
    validate_ceo_response,
    validate_human_response,
)
from data.pipelines.rfp_arbitration import collect_conflicts, run_arbitration  # noqa: E402
from data.pipelines.rfp_final_document import (  # noqa: E402
    SectionSnapshot,
    SynthesisContext,
    SynthesisGateError,
    build_final_document,
)
from data.pipelines.rfp_trace import draft_trace_summary, trace_p3  # noqa: E402
from rfp.constants import (  # noqa: E402
    APPROVAL_DECISION_APPROVE,
    APPROVAL_DECISION_REJECT,
    APPROVAL_DECISION_REQUEST_CHANGES,
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_AWAITING_HUMAN,
    APPROVAL_STATUS_CHANGES_REQUESTED,
    APPROVAL_STATUS_REJECTED,
    CEO_DECISION_APPROVE,
    CEO_DECISION_REJECT,
    ERROR_PIPELINE_ERROR,
    STATUS_ARBITRATING,
    STATUS_AWAITING_CEO_APPROVAL,
    STATUS_AWAITING_DEPARTMENT_APPROVAL,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from rfp.state import RfpGraphState  # noqa: E402

logger = logging.getLogger(__name__)

TERMINAL_DEPT_APPROVAL = frozenset(
    {APPROVAL_STATUS_APPROVED, APPROVAL_STATUS_REJECTED}
)


def _load_generation():
    from data.pipelines import rfp_generation as generation

    return generation


def _approved_drafts(state: RfpGraphState) -> dict[str, str]:
    statuses = state.get("department_approval_statuses") or {}
    drafts = state.get("department_drafts") or {}
    return {
        dept: drafts[dept]
        for dept, status in statuses.items()
        if status == APPROVAL_STATUS_APPROVED and dept in drafts
    }


def _approval_start_node(state: RfpGraphState) -> dict[str, Any]:
    departments = list(state.get("departments_needed") or [])
    return {
        "status": STATUS_AWAITING_DEPARTMENT_APPROVAL,
        "arbitration_round": state.get("arbitration_round") or 0,
        "trace_events": trace_p3(
            "approval_start",
            input_data={"department_count": len(departments)},
            output_data={"status": STATUS_AWAITING_DEPARTMENT_APPROVAL},
        ),
    }


def _route_after_approval_start(
    state: RfpGraphState,
) -> list[Send] | Literal["approval_join"]:
    departments = list(state.get("departments_needed") or [])
    if not departments:
        return "approval_join"
    sends: list[Send] = []
    for dept in departments:
        sends.append(
            Send(
                "dept_approval_branch",
                {
                    "active_department_id": dept,
                    "ticket_id": state.get("ticket_id"),
                    "metadata": state.get("metadata") or {},
                    "department_key_aspects": state.get("department_key_aspects") or {},
                    "department_excerpts": state.get("department_excerpts") or {},
                    "department_drafts": state.get("department_drafts") or {},
                    "department_evaluation_results": state.get("department_evaluation_results") or {},
                    "department_draft_statuses": state.get("department_draft_statuses") or {},
                    "requires_ceo_approval": state.get("requires_ceo_approval"),
                    "conflicts": state.get("conflicts") or [],
                    "intake_summary": state.get("intake_summary") or "",
                },
            )
        )
    return sends


def _dept_approval_branch_node(state: RfpGraphState) -> dict[str, Any]:
    """Per-dept loop: interrupt → validate → approve/reject/regen (M9-P3-4)."""
    dept = state.get("active_department_id")
    if not dept:
        return {}

    ticket_id = state.get("ticket_id") or ""
    metadata = state.get("metadata") or {}
    key_aspects = list((state.get("department_key_aspects") or {}).get(dept) or [])
    drafts = state.get("department_drafts") or {}
    evaluations = state.get("department_evaluation_results") or {}
    draft_statuses = state.get("department_draft_statuses") or {}
    requires_ceo = bool(state.get("requires_ceo_approval"))
    conflicts = list(state.get("conflicts") or [])

    trace_events: list[dict[str, Any]] = []
    department_approval_statuses: dict[str, str] = {}
    department_drafts: dict[str, str] = {}
    department_evaluation_results: dict[str, dict[str, Any]] = {}
    department_draft_statuses: dict[str, str] = {}

    while True:
        draft_content = drafts.get(dept, "")
        draft_status = draft_statuses.get(dept)
        evaluation_results = evaluations.get(dept) or {}

        packet = build_dept_approval_packet(
            ticket_id=ticket_id,
            department_id=dept,
            metadata=metadata,
            key_aspects=key_aspects,
            draft_content=draft_content,
            draft_status=draft_status,
            evaluation_results=evaluation_results,
            requires_ceo_approval=requires_ceo,
            conflicts=conflicts if conflicts else None,
        )

        trace_events.extend(
            trace_p3(
                "prepare_approval_packet",
                input_data={
                    "department_id": dept,
                    **draft_trace_summary(draft_content),
                    "draft_status": draft_status,
                },
                output_data={"approval_status": APPROVAL_STATUS_AWAITING_HUMAN},
            )
        )

        department_approval_statuses[dept] = APPROVAL_STATUS_AWAITING_HUMAN

        resume_payload = interrupt(
            {
                "kind": "dept_approval",
                "department_id": dept,
                "packet": packet,
            }
        )

        trace_events.extend(
            trace_p3(
                "dept_approval_interrupt",
                input_data={"department_id": dept, "draft_status": draft_status},
                output_data={"status": APPROVAL_STATUS_AWAITING_HUMAN},
            )
        )

        try:
            validated = validate_human_response(resume_payload, expected_department_id=dept)
        except ApprovalResponseError as exc:
            trace_events.extend(
                trace_p3(
                    "validate_human_response",
                    input_data={"department_id": dept},
                    output_data={"ok": False, "error": str(exc)},
                )
            )
            raise

        trace_events.extend(
            trace_p3(
                "validate_human_response",
                input_data={"department_id": dept, "decision": validated["decision"]},
                output_data={"ok": True},
            )
        )

        decision = validated["decision"]
        if decision == APPROVAL_DECISION_APPROVE:
            department_approval_statuses[dept] = APPROVAL_STATUS_APPROVED
            trace_events.extend(
                trace_p3(
                    "mark_dept_approved",
                    input_data={"department_id": dept, "approver": validated["approver"]},
                    output_data={"approval_status": APPROVAL_STATUS_APPROVED},
                )
            )
            break

        if decision == APPROVAL_DECISION_REJECT:
            department_approval_statuses[dept] = APPROVAL_STATUS_REJECTED
            trace_events.extend(
                trace_p3(
                    "mark_dept_rejected",
                    input_data={"department_id": dept, "approver": validated["approver"]},
                    output_data={"approval_status": APPROVAL_STATUS_REJECTED},
                )
            )
            break

        # request_changes — dept-scoped P2 regen (M9-P3-7)
        department_approval_statuses[dept] = APPROVAL_STATUS_CHANGES_REQUESTED
        trace_events.extend(
            trace_p3(
                "dept_regen",
                input_data={
                    "department_id": dept,
                    "comment": validated.get("comment"),
                },
                output_data={"approval_status": APPROVAL_STATUS_CHANGES_REQUESTED},
            )
        )

        generation = _load_generation()
        excerpt = (state.get("department_excerpts") or {}).get(dept, "")
        intake_summary = state.get("intake_summary") or ""

        try:
            draft, eval_results, new_draft_status = generation.run_department_generation_loop(
                department_id=dept,
                metadata=metadata,
                key_aspects=key_aspects,
                excerpt=excerpt,
                intake_summary=intake_summary,
                use_llm_relevance=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Dept regen failed for %s", dept)
            return {
                "department_failures": {dept: str(exc)},
                "status": STATUS_FAILED,
                "error_code": ERROR_PIPELINE_ERROR,
                "error_message": f"Department regen failed for {dept}.",
                "trace_events": trace_events,
            }

        drafts = {**drafts, dept: draft}
        evaluations = {**evaluations, dept: eval_results}
        draft_statuses = {**draft_statuses, dept: new_draft_status}
        department_drafts[dept] = draft
        department_evaluation_results[dept] = eval_results
        department_draft_statuses[dept] = new_draft_status

        trace_events.extend(
            trace_p3(
                "dept_regen",
                input_data={"department_id": dept},
                output_data={
                    "draft_status": new_draft_status,
                    **draft_trace_summary(draft),
                },
            )
        )
        # Loop back to interrupt with refreshed draft.

    result: dict[str, Any] = {
        "department_approval_statuses": department_approval_statuses,
        "trace_events": trace_events,
    }
    if department_drafts:
        result["department_drafts"] = department_drafts
    if department_evaluation_results:
        result["department_evaluation_results"] = department_evaluation_results
    if department_draft_statuses:
        result["department_draft_statuses"] = department_draft_statuses
    return result


def _approval_join_node(state: RfpGraphState) -> dict[str, Any]:
    departments = list(state.get("departments_needed") or [])
    statuses = state.get("department_approval_statuses") or {}
    approved = sum(1 for dept in departments if statuses.get(dept) == APPROVAL_STATUS_APPROVED)
    rejected = sum(1 for dept in departments if statuses.get(dept) == APPROVAL_STATUS_REJECTED)
    return {
        "trace_events": trace_p3(
            "approval_join",
            input_data={"departments_needed": departments},
            output_data={
                "approved_count": approved,
                "rejected_count": rejected,
                "statuses": {d: statuses.get(d) for d in departments},
            },
        ),
    }


def _route_after_approval_join(
    state: RfpGraphState,
) -> Literal["detect_conflicts", "approval_finalize"]:
    departments = list(state.get("departments_needed") or [])
    statuses = state.get("department_approval_statuses") or {}
    if any(statuses.get(dept) == APPROVAL_STATUS_REJECTED for dept in departments):
        return "approval_finalize"
    if all(statuses.get(dept) == APPROVAL_STATUS_APPROVED for dept in departments):
        return "detect_conflicts"
    return "approval_finalize"


def _detect_conflicts_node(state: RfpGraphState) -> dict[str, Any]:
    approved = _approved_drafts(state)
    merged = collect_conflicts(
        intake_conflicts=list(state.get("conflicts") or []),
        approved_drafts=approved,
    )
    return {
        "conflicts": merged,
        "trace_events": trace_p3(
            "detect_conflicts",
            input_data={"approved_departments": list(approved.keys())},
            output_data={"conflict_count": len(merged)},
        ),
    }


def _route_after_detect_conflicts(
    state: RfpGraphState,
) -> Literal["arbitration_node", "route_post_arbitration"]:
    conflicts = state.get("conflicts") or []
    if conflicts:
        return "arbitration_node"
    return "route_post_arbitration"


def _arbitration_node(state: RfpGraphState) -> dict[str, Any]:
    conflicts = list(state.get("conflicts") or [])
    current_round = int(state.get("arbitration_round") or 0)
    result = run_arbitration(conflicts)
    new_round = current_round + max(result.rounds_used, 1 if conflicts else 0)
    return {
        "status": STATUS_ARBITRATING,
        "arbitration_round": new_round,
        "arbitration_resolutions": result.resolutions,
        "conflicts": result.remaining_conflicts,
        "arbitration_exhausted": result.arbitration_exhausted,
        "trace_events": trace_p3(
            "arbitration_node",
            input_data={"conflict_count": len(conflicts), "round": new_round},
            output_data={
                "resolutions_count": len(result.resolutions),
                "remaining_conflicts": len(result.remaining_conflicts),
                "arbitration_exhausted": result.arbitration_exhausted,
            },
        ),
    }


def _route_post_arbitration_node(state: RfpGraphState) -> dict[str, Any]:
    """Passthrough routing hub after arbitration or when no conflicts."""
    return {}


def _route_after_arbitration(
    state: RfpGraphState,
) -> Literal["ceo_approval_interrupt", "ultimate_document_synthesizer", "approval_finalize"]:
    if state.get("arbitration_exhausted"):
        return "approval_finalize"
    if state.get("requires_ceo_approval"):
        return "ceo_approval_interrupt"
    return "ultimate_document_synthesizer"


def _ceo_approval_interrupt_node(state: RfpGraphState) -> dict[str, Any]:
    approved = _approved_drafts(state)
    packet = build_ceo_approval_packet(
        ticket_id=state.get("ticket_id") or "",
        metadata=state.get("metadata") or {},
        requires_ceo_approval=bool(state.get("requires_ceo_approval")),
        approved_excerpts=approved,
        arbitration_resolutions=list(state.get("arbitration_resolutions") or []),
        remaining_conflicts=list(state.get("conflicts") or []),
    )

    resume_payload = interrupt(
        {
            "kind": "ceo_approval",
            "packet": packet,
        }
    )

    trace_events = trace_p3(
        "ceo_approval_interrupt",
        input_data={"requires_ceo_approval": True},
        output_data={"status": STATUS_AWAITING_CEO_APPROVAL},
    )

    try:
        validated = validate_ceo_response(resume_payload)
    except ApprovalResponseError as exc:
        trace_events.extend(
            trace_p3(
                "validate_ceo_response",
                input_data={},
                output_data={"ok": False, "error": str(exc)},
            )
        )
        raise

    trace_events.extend(
        trace_p3(
            "validate_ceo_response",
            input_data={"decision": validated["decision"]},
            output_data={"ok": True},
        )
    )

    if validated["decision"] == CEO_DECISION_REJECT:
        return {
            "status": STATUS_AWAITING_CEO_APPROVAL,
            "ceo_approved": False,
            "trace_events": trace_events,
        }

    return {
        "status": STATUS_AWAITING_CEO_APPROVAL,
        "ceo_approved": True,
        "trace_events": trace_events,
    }


def _route_after_ceo(
    state: RfpGraphState,
) -> Literal["ultimate_document_synthesizer", "approval_finalize"]:
    if state.get("ceo_approved"):
        return "ultimate_document_synthesizer"
    return "approval_finalize"


def _ultimate_document_synthesizer_node(state: RfpGraphState) -> dict[str, Any]:
    departments = list(state.get("departments_needed") or [])
    statuses = state.get("department_approval_statuses") or {}
    drafts = state.get("department_drafts") or {}

    sections = [
        SectionSnapshot(
            department_id=dept,
            draft_content=drafts.get(dept, ""),
            approval_status=statuses.get(dept),
        )
        for dept in departments
    ]

    ctx = SynthesisContext(
        metadata=dict(state.get("metadata") or {}),
        intake_summary=state.get("intake_summary") or "",
        departments_needed=departments,
        sections=sections,
        arbitration_resolutions=list(state.get("arbitration_resolutions") or []),
        requires_ceo_approval=bool(state.get("requires_ceo_approval")),
        ceo_approved=bool(state.get("ceo_approved")),
        arbitration_exhausted=bool(state.get("arbitration_exhausted")),
    )

    try:
        final_md = build_final_document(ctx)
    except SynthesisGateError as exc:
        logger.error("Synthesis gate blocked: %s", exc)
        return {
            "status": STATUS_AWAITING_DEPARTMENT_APPROVAL,
            "error_message": str(exc),
            "trace_events": trace_p3(
                "ultimate_document_synthesizer",
                input_data={"departments_needed": departments},
                output_data={"ok": False, "error": str(exc)},
            ),
        }

    generated_at = datetime.now(timezone.utc)
    return {
        "final_document_markdown": final_md,
        "status": STATUS_COMPLETED,
        "trace_events": trace_p3(
            "ultimate_document_synthesizer",
            input_data={"departments_needed": departments},
            output_data={
                "ok": True,
                "final_document_length": len(final_md),
                "generated_at": generated_at.isoformat(),
            },
        ),
    }


def _approval_finalize_node(state: RfpGraphState) -> dict[str, Any]:
    status = state.get("status") or STATUS_AWAITING_DEPARTMENT_APPROVAL
    if status != STATUS_COMPLETED:
        statuses = state.get("department_approval_statuses") or {}
        if state.get("arbitration_exhausted"):
            status = STATUS_ARBITRATING
        elif any(s == APPROVAL_STATUS_REJECTED for s in statuses.values()):
            status = STATUS_AWAITING_DEPARTMENT_APPROVAL
        elif state.get("requires_ceo_approval") and not state.get("ceo_approved"):
            status = STATUS_AWAITING_CEO_APPROVAL

    return {
        "status": status,
        "trace_events": trace_p3(
            "approval_finalize",
            input_data={"ticket_id": state.get("ticket_id")},
            output_data={"status": status, "completed": status == STATUS_COMPLETED},
        ),
    }


def add_approval_nodes(builder) -> None:
    """Attach P3 nodes and edges to the shared RFP StateGraph builder."""
    builder.add_node("approval_start", _approval_start_node)
    builder.add_node("dept_approval_branch", _dept_approval_branch_node)
    builder.add_node("approval_join", _approval_join_node)
    builder.add_node("detect_conflicts", _detect_conflicts_node)
    builder.add_node("arbitration_node", _arbitration_node)
    builder.add_node("route_post_arbitration", _route_post_arbitration_node)
    builder.add_node("ceo_approval_interrupt", _ceo_approval_interrupt_node)
    builder.add_node("ultimate_document_synthesizer", _ultimate_document_synthesizer_node)
    builder.add_node("approval_finalize", _approval_finalize_node)

    builder.add_conditional_edges(
        "approval_start",
        _route_after_approval_start,
        ["dept_approval_branch", "approval_join"],
    )
    builder.add_edge("dept_approval_branch", "approval_join")
    builder.add_conditional_edges(
        "approval_join",
        _route_after_approval_join,
        {"detect_conflicts": "detect_conflicts", "approval_finalize": "approval_finalize"},
    )
    builder.add_conditional_edges(
        "detect_conflicts",
        _route_after_detect_conflicts,
        {"arbitration_node": "arbitration_node", "route_post_arbitration": "route_post_arbitration"},
    )
    builder.add_edge("arbitration_node", "route_post_arbitration")
    builder.add_conditional_edges(
        "route_post_arbitration",
        _route_after_arbitration,
        {
            "ceo_approval_interrupt": "ceo_approval_interrupt",
            "ultimate_document_synthesizer": "ultimate_document_synthesizer",
            "approval_finalize": "approval_finalize",
        },
    )
    builder.add_conditional_edges(
        "ceo_approval_interrupt",
        _route_after_ceo,
        {
            "ultimate_document_synthesizer": "ultimate_document_synthesizer",
            "approval_finalize": "approval_finalize",
        },
    )
    builder.add_edge("ultimate_document_synthesizer", "approval_finalize")
    builder.add_edge("approval_finalize", END)


def extend_entry_router(
    route_entry_fn,
):
    """Deprecated — entry routing lives in ``rfp_generation_graph._route_entry``."""
    return route_entry_fn


__all__ = [
    "add_approval_nodes",
]
