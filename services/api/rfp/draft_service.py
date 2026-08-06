"""Orchestrate RFP Part 2 generation graph and Postgres persistence."""

from __future__ import annotations

import logging
import threading
from typing import Any

from sqlmodel import Session

from database import get_engine
from data.pipelines.rfp_intake import build_department_excerpt
from data.pipelines.rfp_intake_graph import invoke_rfp_generation
from rfp.constants import (
    DRAFT_STATUS_PENDING,
    STATUS_DRAFTING,
    STATUS_FAILED,
    STATUS_INTAKE_COMPLETE,
    STATUS_UNDER_EVALUATION,
    TERMINAL_DRAFT_STATUSES,
)
from rfp.intake_service import ensure_ticket_markdown
from rfp.repository import (
    append_trace_event,
    get_ticket,
    get_ticket_or_raise,
    list_sections,
    update_department_section,
    update_ticket,
)
from rfp.state import RfpGraphState, initial_generation_state

logger = logging.getLogger(__name__)

_draft_lock = threading.Lock()
_draft_running: set[str] = set()


class DraftNotAllowedError(ValueError):
    """Raised when P2 draft cannot start from the ticket's current status."""

    def __init__(self, current_status: str) -> None:
        self.current_status = current_status
        super().__init__(
            f"Draft cannot start from status '{current_status}' "
            f"(requires '{STATUS_INTAKE_COMPLETE}')."
        )


def hydrate_generation_state(session: Session, ticket_id: str) -> RfpGraphState:
    """Load ticket + sections from Postgres for P2 graph entry (M9-P2-14)."""
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
    return initial_generation_state(
        ticket_id=ticket_id,
        metadata=dict(ticket.metadata_json or {}),
        departments_needed=list(ticket.departments_needed or []),
        department_key_aspects=key_aspects,
        department_excerpts=excerpts,
        intake_summary=ticket.intake_summary or "",
        requires_ceo_approval=bool(ticket.requires_ceo_approval),
        conflicts=list(ticket.conflicts or []),
        markdown_text=markdown,
    )


def _sync_ticket_status_during_generation(session: Session, ticket_id: str) -> None:
    """Move ticket to under_evaluation once any section finishes but others remain."""
    ticket = get_ticket_or_raise(session, ticket_id)
    sections = list_sections(session, ticket_id)
    if not sections:
        return

    terminal_count = sum(
        1
        for section in sections
        if (section.draft_status or DRAFT_STATUS_PENDING) in TERMINAL_DRAFT_STATUSES
    )
    if terminal_count == len(sections):
        return
    if terminal_count > 0 and ticket.status != STATUS_UNDER_EVALUATION:
        update_ticket(session, ticket_id, status=STATUS_UNDER_EVALUATION)


def persist_department_generation_update(
    session: Session,
    ticket_id: str,
    update: dict[str, Any],
) -> None:
    """Persist one parallel branch output as soon as a department finishes (P2 UX)."""
    drafts = update.get("department_drafts") or {}
    evaluations = update.get("department_evaluation_results") or {}
    statuses = update.get("department_draft_statuses") or {}
    department_ids = set(drafts) | set(evaluations) | set(statuses)
    for dept in department_ids:
        if dept not in drafts and dept not in evaluations:
            continue
        update_department_section(
            session,
            ticket_id=ticket_id,
            department_id=dept,
            draft_content=drafts.get(dept),
            evaluation_results=evaluations.get(dept),
            draft_status=statuses.get(dept),
        )
    _sync_ticket_status_during_generation(session, ticket_id)


def persist_generation_state(session: Session, ticket_id: str, state: dict[str, Any]) -> None:
    """Write P2 graph results to Postgres (M9-P2-M1 poll source of truth)."""
    status = state.get("status") or STATUS_FAILED
    update_ticket(session, ticket_id, status=status)

    if status == STATUS_FAILED:
        update_ticket(
            session,
            ticket_id,
            error_message=state.get("error_message"),
            error_code=state.get("error_code"),
        )

    drafts = state.get("department_drafts") or {}
    evaluations = state.get("department_evaluation_results") or {}
    draft_statuses = state.get("department_draft_statuses") or {}

    for dept in state.get("departments_needed") or []:
        if dept not in drafts and dept not in evaluations:
            continue
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


def prepare_draft_start(session: Session, ticket_id: str) -> None:
    """Validate intake_complete and mark ticket drafting (M9-P2-4 / M9-P2-16)."""
    ticket = get_ticket_or_raise(session, ticket_id)
    if ticket.status != STATUS_INTAKE_COMPLETE:
        raise DraftNotAllowedError(ticket.status)

    update_ticket(session, ticket_id, status=STATUS_DRAFTING)
    for section in list_sections(session, ticket_id):
        if not section.draft_status:
            update_department_section(
                session,
                ticket_id=ticket_id,
                department_id=section.department_id,
                draft_status=DRAFT_STATUS_PENDING,
            )


def run_generation_for_ticket(session: Session, ticket_id: str) -> None:
    """Hydrate from Postgres, invoke P2 graph, persist results."""
    ticket = get_ticket_or_raise(session, ticket_id)
    if ticket.status not in (STATUS_INTAKE_COMPLETE, STATUS_DRAFTING):
        logger.info(
            "Skipping generation for ticket %s — status is %s",
            ticket_id,
            ticket.status,
        )
        return

    if ticket.status == STATUS_INTAKE_COMPLETE:
        update_ticket(session, ticket_id, status=STATUS_DRAFTING)

    state = hydrate_generation_state(session, ticket_id)

    def on_node_update(node_name: str, update: dict[str, Any]) -> None:
        if node_name == "generate_eval_dept":
            with Session(get_engine()) as branch_session:
                persist_department_generation_update(branch_session, ticket_id, update)

    result = invoke_rfp_generation(state, on_node_update=on_node_update)
    persist_generation_state(session, ticket_id, result)


def run_draft_background_task(ticket_id: str) -> None:
    """BackgroundTasks entrypoint — guard against duplicate concurrent draft runs."""
    with _draft_lock:
        if ticket_id in _draft_running:
            logger.info("Skipping duplicate draft run for ticket %s", ticket_id)
            return
        _draft_running.add(ticket_id)
    try:
        with Session(get_engine()) as session:
            ticket = get_ticket(session, ticket_id)
            if ticket is None or ticket.status != STATUS_DRAFTING:
                return
            run_generation_for_ticket(session, ticket_id)
    except Exception:  # noqa: BLE001 — persist failed status, never crash worker
        logger.exception("RFP draft background task failed for %s", ticket_id)
        try:
            with Session(get_engine()) as session:
                update_ticket(
                    session,
                    ticket_id,
                    status=STATUS_FAILED,
                    error_code="pipeline_error",
                    error_message="RFP draft generation failed unexpectedly.",
                )
        except Exception:
            logger.exception("Could not persist failed status for draft %s", ticket_id)
    finally:
        with _draft_lock:
            _draft_running.discard(ticket_id)


__all__ = [
    "DraftNotAllowedError",
    "hydrate_generation_state",
    "persist_department_generation_update",
    "persist_generation_state",
    "prepare_draft_start",
    "run_draft_background_task",
    "run_generation_for_ticket",
]
