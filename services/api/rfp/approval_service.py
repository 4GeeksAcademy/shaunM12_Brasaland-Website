"""Orchestrate RFP Part 3 approval graph and Postgres persistence."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from database import get_engine
from data.pipelines.rfp_intake import build_department_excerpt
from data.pipelines.rfp_intake_graph import (
    approval_thread_id,
    invoke_rfp_approval,
    list_pending_interrupts,
    reopen_department_approval,
    resume_rfp_approval,
)
from data.pipelines.rfp_approval_packet import ApprovalResponseError, validate_ceo_response
from rfp.constants import (
    APPROVAL_DECISION_APPROVE,
    APPROVAL_DECISION_REJECT,
    APPROVAL_DECISION_REQUEST_CHANGES,
    APPROVAL_DECISION_VALUES,
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_AWAITING_HUMAN,
    APPROVAL_STATUS_CHANGES_REQUESTED,
    APPROVAL_STATUS_REJECTED,
    CEO_DECISION_VALUES,
    DEPARTMENT_IDS,
    DRAFT_STATUS_DRAFTING,
    STATUS_ARBITRATING,
    STATUS_AWAITING_CEO_APPROVAL,
    STATUS_AWAITING_DEPARTMENT_APPROVAL,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_WAITING_FOR_APPROVAL,
    approval_status_label,
)
from rfp.intake_service import ensure_ticket_markdown, write_final_proposal_mirror
from rfp.repository import (
    RfpSectionNotFoundError,
    RfpTicketNotFoundError,
    append_trace_event,
    get_section,
    get_section_or_raise,
    get_ticket,
    get_ticket_or_raise,
    list_sections,
    ticket_detail,
    update_department_section,
    update_ticket,
)
from rfp.state import RfpGraphState, initial_approval_state

logger = logging.getLogger(__name__)

_approval_lock = threading.Lock()
_approval_running: set[str] = set()


class ApprovalNotAllowedError(ValueError):
    """Raised when P3 approval cannot start from the ticket's current status."""

    def __init__(self, current_status: str) -> None:
        self.current_status = current_status
        super().__init__(
            f"Approval cannot start from status '{current_status}' "
            f"(requires '{STATUS_WAITING_FOR_APPROVAL}')."
        )


class DecisionNotAllowedError(ValueError):
    """Raised when a human/CEO decision cannot be applied in the current phase."""

    def __init__(self, message: str, *, current_status: str | None = None) -> None:
        self.current_status = current_status
        super().__init__(message)


class NoPendingInterruptError(ValueError):
    """Raised when no LangGraph interrupt matches the requested decision target."""


class FinalDocumentNotFoundError(LookupError):
    """Raised when a ticket has no synthesized final document yet."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _approval_config(ticket_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": approval_thread_id(ticket_id)}}


def _interrupt_department_id(intr: Any) -> str | None:
    value = intr.value if hasattr(intr, "value") else {}
    if not isinstance(value, dict) or value.get("kind") != "dept_approval":
        return None
    dept = value.get("department_id")
    return str(dept) if dept else None


def _has_dept_interrupt(pending: list[Any], department_id: str) -> bool:
    return any(_interrupt_department_id(intr) == department_id for intr in pending)


def _has_ceo_interrupt(pending: list[Any]) -> bool:
    for intr in pending:
        value = intr.value if hasattr(intr, "value") else {}
        if isinstance(value, dict) and value.get("kind") == "ceo_approval":
            return True
    return False


def _branch_payload_for_department(
    state: RfpGraphState,
    department_id: str,
) -> dict[str, Any]:
    return {
        "active_department_id": department_id,
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
    }


def hydrate_approval_state(session: Session, ticket_id: str) -> RfpGraphState:
    """Load ticket + sections from Postgres for P3 graph entry."""
    ticket = get_ticket_or_raise(session, ticket_id)
    sections = list_sections(session, ticket_id)
    key_aspects = {
        section.department_id: list(section.key_aspects or [])
        for section in sections
    }
    markdown = ensure_ticket_markdown(session, ticket_id)
    excerpts = {
        section.department_id: build_department_excerpt(markdown, section.department_id)
        for section in sections
    }
    drafts = {
        section.department_id: section.draft_content or ""
        for section in sections
        if section.draft_content
    }
    evaluations = {
        section.department_id: dict(section.evaluation_results or {})
        for section in sections
        if section.evaluation_results
    }
    draft_statuses = {
        section.department_id: section.draft_status or ""
        for section in sections
        if section.draft_status
    }
    return initial_approval_state(
        ticket_id=ticket_id,
        metadata=dict(ticket.metadata_json or {}),
        departments_needed=list(ticket.departments_needed or []),
        department_drafts=drafts,
        department_evaluation_results=evaluations,
        department_draft_statuses=draft_statuses,
        department_key_aspects=key_aspects,
        department_excerpts=excerpts,
        intake_summary=ticket.intake_summary or "",
        requires_ceo_approval=bool(ticket.requires_ceo_approval),
        conflicts=list(ticket.conflicts or []),
        markdown_text=markdown,
        arbitration_resolutions=list(ticket.arbitration_resolutions or []),
        arbitration_exhausted=bool(ticket.arbitration_exhausted),
    )


def _persist_interrupt_sections(
    session: Session,
    ticket_id: str,
    interrupts: list[Any],
) -> None:
    """Mark sections awaiting_human from pending dept approval interrupts."""
    for intr in interrupts:
        value = intr.value if hasattr(intr, "value") else intr.get("value")
        if not isinstance(value, dict):
            continue
        if value.get("kind") != "dept_approval":
            continue
        dept = value.get("department_id")
        if not dept:
            continue
        department_id = str(dept)
        section = get_section(
            session,
            ticket_id=ticket_id,
            department_id=department_id,
        )
        if section is None:
            continue
        if section.approval_status in (
            APPROVAL_STATUS_APPROVED,
            APPROVAL_STATUS_REJECTED,
        ):
            continue
        update_department_section(
            session,
            ticket_id=ticket_id,
            department_id=department_id,
            approval_status=APPROVAL_STATUS_AWAITING_HUMAN,
        )


def _sync_arbitration_from_state(
    session: Session,
    ticket_id: str,
    state: dict[str, Any],
) -> None:
    """Persist arbitration resolutions/exhaustion from graph state to Postgres."""
    fields: dict[str, Any] = {}
    if state.get("arbitration_resolutions") is not None:
        fields["arbitration_resolutions"] = list(state.get("arbitration_resolutions") or [])
    if "arbitration_exhausted" in state:
        fields["arbitration_exhausted"] = bool(state.get("arbitration_exhausted"))
    if fields:
        update_ticket(session, ticket_id, **fields)


def persist_approval_state(session: Session, ticket_id: str, state: dict[str, Any]) -> None:
    """Write P3 graph results to Postgres (M9-P2-M1 poll source of truth)."""
    status = state.get("status") or STATUS_AWAITING_DEPARTMENT_APPROVAL
    update_fields: dict[str, Any] = {"status": status}

    if status == STATUS_FAILED:
        update_fields["error_message"] = state.get("error_message")
        update_fields["error_code"] = state.get("error_code")

    if state.get("final_document_markdown") is not None:
        update_fields["final_document_markdown"] = state.get("final_document_markdown")
        update_fields["final_document_generated_at"] = datetime.now(timezone.utc)

    if "arbitration_exhausted" in state:
        update_fields["arbitration_exhausted"] = bool(state.get("arbitration_exhausted"))

    if state.get("arbitration_resolutions") is not None:
        update_fields["arbitration_resolutions"] = list(
            state.get("arbitration_resolutions") or []
        )

    update_ticket(session, ticket_id, **update_fields)

    if state.get("final_document_markdown"):
        try:
            write_final_proposal_mirror(
                ticket_id,
                str(state.get("final_document_markdown") or ""),
            )
        except Exception:  # noqa: BLE001 — DB is source of truth
            logger.exception("Could not write final_proposal.md mirror for %s", ticket_id)

    approval_statuses = state.get("department_approval_statuses") or {}
    for dept, approval_status in approval_statuses.items():
        update_department_section(
            session,
            ticket_id=ticket_id,
            department_id=dept,
            approval_status=approval_status,
        )

    drafts = state.get("department_drafts") or {}
    evaluations = state.get("department_evaluation_results") or {}
    draft_statuses = state.get("department_draft_statuses") or {}
    for dept in set(drafts) | set(evaluations) | set(draft_statuses):
        update_department_section(
            session,
            ticket_id=ticket_id,
            department_id=dept,
            draft_content=drafts.get(dept),
            evaluation_results=evaluations.get(dept),
            draft_status=draft_statuses.get(dept),
        )

    for event in state.get("trace_events") or []:
        node = str(event.get("node") or "unknown")
        append_trace_event(session, ticket_id=ticket_id, node=node, payload=dict(event))


def persist_approval_interrupt(session: Session, ticket_id: str, state: dict[str, Any]) -> None:
    """Persist ticket/sections when graph pauses at dept or CEO interrupts."""
    interrupts = list(state.get("__interrupt__") or [])
    if not interrupts:
        config = {"configurable": {"thread_id": approval_thread_id(ticket_id)}}
        interrupts = list_pending_interrupts(config)

    update_ticket(session, ticket_id, status=STATUS_AWAITING_DEPARTMENT_APPROVAL)
    _persist_interrupt_sections(session, ticket_id, interrupts)

    ceo_waiting = any(
        (intr.value if hasattr(intr, "value") else {}).get("kind") == "ceo_approval"
        for intr in interrupts
    )
    if ceo_waiting:
        update_ticket(session, ticket_id, status=STATUS_AWAITING_CEO_APPROVAL)

    _sync_arbitration_from_state(session, ticket_id, state)

    for event in state.get("trace_events") or []:
        node = str(event.get("node") or "unknown")
        append_trace_event(session, ticket_id=ticket_id, node=node, payload=dict(event))


def run_approval_for_ticket(session: Session, ticket_id: str) -> None:
    """Hydrate from Postgres, invoke P3 graph, persist results or interrupt state."""
    ticket = get_ticket_or_raise(session, ticket_id)
    if ticket.status != STATUS_WAITING_FOR_APPROVAL:
        logger.info(
            "Skipping approval for ticket %s — status is %s",
            ticket_id,
            ticket.status,
        )
        return

    state = hydrate_approval_state(session, ticket_id)
    result = invoke_rfp_approval(state)

    if result.get("__interrupt__") or list_pending_interrupts(
        {"configurable": {"thread_id": approval_thread_id(ticket_id)}}
    ):
        persist_approval_interrupt(session, ticket_id, result)
        return

    persist_approval_state(session, ticket_id, result)


def run_approval_background_task(ticket_id: str) -> None:
    """BackgroundTasks entrypoint — guard against duplicate concurrent approval runs."""
    with _approval_lock:
        if ticket_id in _approval_running:
            logger.info("Skipping duplicate approval run for ticket %s", ticket_id)
            return
        _approval_running.add(ticket_id)
    try:
        with Session(get_engine()) as session:
            ticket = get_ticket(session, ticket_id)
            if ticket is None or ticket.status != STATUS_WAITING_FOR_APPROVAL:
                return
            run_approval_for_ticket(session, ticket_id)
    except Exception:  # noqa: BLE001 — persist failed status, never crash worker
        logger.exception("RFP approval background task failed for %s", ticket_id)
        try:
            with Session(get_engine()) as session:
                update_ticket(
                    session,
                    ticket_id,
                    status=STATUS_FAILED,
                    error_code="pipeline_error",
                    error_message="RFP approval pipeline failed unexpectedly.",
                )
        except Exception:
            logger.exception("Could not persist failed status for approval %s", ticket_id)
    finally:
        with _approval_lock:
            _approval_running.discard(ticket_id)


def resume_approval_for_ticket(
    session: Session,
    ticket_id: str,
    payload: dict[str, Any],
    *,
    interrupt_id: str | None = None,
) -> dict[str, Any]:
    """Resume graph after human/CEO decision POST (Phase 3 API will call this)."""
    result = resume_rfp_approval(ticket_id, payload, interrupt_id=interrupt_id)
    if result.get("__interrupt__") or list_pending_interrupts(
        {"configurable": {"thread_id": approval_thread_id(ticket_id)}}
    ):
        persist_approval_interrupt(session, ticket_id, result)
    else:
        persist_approval_state(session, ticket_id, result)
    return result


def start_approval_recovery(session: Session, ticket_id: str) -> None:
    """Recovery-only idempotent P3 start (M9-P3-3)."""
    ticket = get_ticket_or_raise(session, ticket_id)
    if ticket.status == STATUS_WAITING_FOR_APPROVAL:
        run_approval_for_ticket(session, ticket_id)
        return
    if ticket.status in (
        STATUS_AWAITING_DEPARTMENT_APPROVAL,
        STATUS_AWAITING_CEO_APPROVAL,
        STATUS_ARBITRATING,
        STATUS_COMPLETED,
    ):
        return
    raise ApprovalNotAllowedError(ticket.status)


def submit_department_decision(
    session: Session,
    *,
    ticket_id: str,
    department_id: str,
    decision: str,
    approver: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """Validate, persist Postgres, then resume the dept approval interrupt."""
    if department_id not in DEPARTMENT_IDS:
        raise RfpSectionNotFoundError(
            f"RFP section not found: ticket={ticket_id} department={department_id}"
        )

    ticket = get_ticket_or_raise(session, ticket_id)
    if ticket.status != STATUS_AWAITING_DEPARTMENT_APPROVAL:
        raise DecisionNotAllowedError(
            f"Department decisions require status '{STATUS_AWAITING_DEPARTMENT_APPROVAL}'.",
            current_status=ticket.status,
        )

    section = get_section_or_raise(
        session,
        ticket_id=ticket_id,
        department_id=department_id,
    )
    if section.approval_status != APPROVAL_STATUS_AWAITING_HUMAN:
        raise DecisionNotAllowedError(
            f"Section '{department_id}' is not awaiting human approval "
            f"(current: {section.approval_status!r}).",
            current_status=ticket.status,
        )

    if decision not in APPROVAL_DECISION_VALUES:
        raise ApprovalResponseError(
            f"Invalid decision '{decision}'. Expected one of: {sorted(APPROVAL_DECISION_VALUES)}."
        )

    pending = list_pending_interrupts(_approval_config(ticket_id))
    if not _has_dept_interrupt(pending, department_id):
        raise NoPendingInterruptError(
            f"No pending approval interrupt for department '{department_id}'."
        )

    now = _utc_now()
    comment_text = (comment or "").strip() or None
    if decision == APPROVAL_DECISION_APPROVE:
        update_department_section(
            session,
            ticket_id=ticket_id,
            department_id=department_id,
            approval_status=APPROVAL_STATUS_APPROVED,
            approver=approver,
            approved_at=now,
            approval_comment=comment_text,
        )
    elif decision == APPROVAL_DECISION_REJECT:
        update_department_section(
            session,
            ticket_id=ticket_id,
            department_id=department_id,
            approval_status=APPROVAL_STATUS_REJECTED,
            approver=approver,
            approved_at=now,
            approval_comment=comment_text,
        )
    else:
        update_department_section(
            session,
            ticket_id=ticket_id,
            department_id=department_id,
            approval_status=APPROVAL_STATUS_CHANGES_REQUESTED,
            approver=approver,
            approved_at=None,
            approval_comment=comment_text,
        )

    payload = {
        "kind": "dept_approval",
        "department_id": department_id,
        "decision": decision,
        "approver": approver,
        "comment": comment or "",
    }
    resume_approval_for_ticket(session, ticket_id, payload)
    detail = ticket_detail(session, ticket_id)
    section_row = next(s for s in detail.sections if s.department_id == department_id)
    return {
        "ticket_id": ticket_id,
        "department_id": department_id,
        "decision": decision,
        "status": detail.status,
        "status_label": detail.status_label,
        "approval_status": section_row.approval_status,
        "approval_status_label": section_row.approval_status_label,
    }


def regenerate_department_section(
    session: Session,
    *,
    ticket_id: str,
    department_id: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """Reject recovery — dept-scoped regen and re-interrupt (M9-P3-7)."""
    if department_id not in DEPARTMENT_IDS:
        raise RfpSectionNotFoundError(
            f"RFP section not found: ticket={ticket_id} department={department_id}"
        )

    ticket = get_ticket_or_raise(session, ticket_id)
    if ticket.status not in (STATUS_AWAITING_DEPARTMENT_APPROVAL, STATUS_ARBITRATING):
        raise DecisionNotAllowedError(
            "Regenerate is only available during department approval.",
            current_status=ticket.status,
        )

    section = get_section_or_raise(
        session,
        ticket_id=ticket_id,
        department_id=department_id,
    )
    if section.approval_status != APPROVAL_STATUS_REJECTED:
        raise DecisionNotAllowedError(
            f"Regenerate requires section '{department_id}' to be rejected "
            f"(current: {section.approval_status!r}).",
            current_status=ticket.status,
        )

    update_department_section(
        session,
        ticket_id=ticket_id,
        department_id=department_id,
        draft_status=DRAFT_STATUS_DRAFTING,
        clear_approval_fields=True,
    )

    from data.pipelines import rfp_generation as generation

    state = hydrate_approval_state(session, ticket_id)
    key_aspects = list((state.get("department_key_aspects") or {}).get(department_id) or [])
    excerpt = (state.get("department_excerpts") or {}).get(department_id, "")
    metadata = state.get("metadata") or {}

    draft, evaluation_results, draft_status = generation.run_department_generation_loop(
        department_id=department_id,
        metadata=metadata,
        key_aspects=key_aspects,
        excerpt=excerpt,
        intake_summary=state.get("intake_summary") or "",
        use_llm_relevance=False,
    )
    update_department_section(
        session,
        ticket_id=ticket_id,
        department_id=department_id,
        draft_content=draft,
        evaluation_results=evaluation_results,
        draft_status=draft_status,
    )

    pending = list_pending_interrupts(_approval_config(ticket_id))
    if _has_dept_interrupt(pending, department_id):
        update_department_section(
            session,
            ticket_id=ticket_id,
            department_id=department_id,
            approval_status=APPROVAL_STATUS_AWAITING_HUMAN,
        )
        update_ticket(session, ticket_id, status=STATUS_AWAITING_DEPARTMENT_APPROVAL)
        detail = ticket_detail(session, ticket_id)
        section_row = next(s for s in detail.sections if s.department_id == department_id)
        return {
            "ticket_id": ticket_id,
            "department_id": department_id,
            "status": detail.status,
            "status_label": detail.status_label,
            "draft_status": section_row.draft_status,
            "draft_status_label": section_row.draft_status_label,
            "approval_status": section_row.approval_status,
            "approval_status_label": section_row.approval_status_label,
        }

    state = hydrate_approval_state(session, ticket_id)
    branch_payload = _branch_payload_for_department(state, department_id)
    result = reopen_department_approval(ticket_id, branch_payload)
    pending = list_pending_interrupts(_approval_config(ticket_id))
    has_interrupt = bool(result.get("__interrupt__") or _has_dept_interrupt(pending, department_id))

    if has_interrupt:
        persist_approval_interrupt(session, ticket_id, result)
        update_department_section(
            session,
            ticket_id=ticket_id,
            department_id=department_id,
            approval_status=APPROVAL_STATUS_AWAITING_HUMAN,
        )
    elif result.get("status") == STATUS_FAILED:
        raise DecisionNotAllowedError(
            result.get("error_message") or "Department regenerate failed.",
            current_status=ticket.status,
        )
    else:
        raise DecisionNotAllowedError(
            f"Could not re-open approval interrupt for department '{department_id}'.",
            current_status=ticket.status,
        )

    detail = ticket_detail(session, ticket_id)
    section_row = next(s for s in detail.sections if s.department_id == department_id)
    return {
        "ticket_id": ticket_id,
        "department_id": department_id,
        "status": detail.status,
        "status_label": detail.status_label,
        "draft_status": section_row.draft_status,
        "draft_status_label": section_row.draft_status_label,
        "approval_status": section_row.approval_status,
        "approval_status_label": section_row.approval_status_label,
    }


def submit_ceo_decision(
    session: Session,
    *,
    ticket_id: str,
    decision: str,
    approver: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """Validate, persist trace metadata, then resume the CEO interrupt."""
    ticket = get_ticket_or_raise(session, ticket_id)
    if not ticket.requires_ceo_approval:
        raise DecisionNotAllowedError(
            "CEO decision is not required for this ticket.",
            current_status=ticket.status,
        )
    if ticket.status != STATUS_AWAITING_CEO_APPROVAL:
        raise DecisionNotAllowedError(
            f"CEO decisions require status '{STATUS_AWAITING_CEO_APPROVAL}'.",
            current_status=ticket.status,
        )
    if decision not in CEO_DECISION_VALUES:
        raise ApprovalResponseError(
            f"Invalid CEO decision '{decision}'. Expected one of: {sorted(CEO_DECISION_VALUES)}."
        )

    pending = list_pending_interrupts(_approval_config(ticket_id))
    if not _has_ceo_interrupt(pending):
        raise NoPendingInterruptError("No pending CEO approval interrupt.")

    update_ticket(
        session,
        ticket_id,
        ceo_approval_comment=(comment or "").strip() or None,
    )

    payload = {
        "kind": "ceo_approval",
        "decision": decision,
        "approver": approver,
        "comment": comment or "",
    }
    resume_approval_for_ticket(session, ticket_id, payload)
    detail = ticket_detail(session, ticket_id)
    return {
        "ticket_id": ticket_id,
        "decision": decision,
        "status": detail.status,
        "status_label": detail.status_label,
    }


def get_final_document(session: Session, ticket_id: str) -> dict[str, Any]:
    """Return merged final proposal markdown when synthesis completed."""
    ticket = get_ticket_or_raise(session, ticket_id)
    if not ticket.final_document_markdown:
        raise FinalDocumentNotFoundError(f"No final document for ticket {ticket_id}.")
    if ticket.final_document_generated_at is None:
        raise FinalDocumentNotFoundError(f"No final document timestamp for ticket {ticket_id}.")
    return {
        "ticket_id": ticket_id,
        "final_document_markdown": ticket.final_document_markdown,
        "generated_at": ticket.final_document_generated_at,
    }


__all__ = [
    "ApprovalNotAllowedError",
    "DecisionNotAllowedError",
    "FinalDocumentNotFoundError",
    "NoPendingInterruptError",
    "get_final_document",
    "hydrate_approval_state",
    "persist_approval_interrupt",
    "persist_approval_state",
    "regenerate_department_section",
    "resume_approval_for_ticket",
    "run_approval_background_task",
    "run_approval_for_ticket",
    "start_approval_recovery",
    "submit_ceo_decision",
    "submit_department_decision",
]
