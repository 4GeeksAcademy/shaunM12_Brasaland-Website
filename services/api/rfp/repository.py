"""Persistence layer for RFP tickets, sections, and trace events."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlmodel import Session, select

from .constants import (
    APPROVAL_STATUS_APPROVED,
    DRAFT_STATUS_PENDING,
    STATUS_ANALYZING,
    STATUS_AWAITING_CEO_APPROVAL,
    approval_status_label,
    department_label,
    department_owner,
    draft_status_label,
    status_label,
)
from .models import RfpDepartmentSection, RfpTicket, RfpTraceEvent
from .schemas import (
    RfpCeoApprovalPacketResponse,
    RfpSectionResponse,
    RfpTicketDetailResponse,
    RfpTicketSummaryResponse,
    RfpTraceEventResponse,
)

logger = logging.getLogger(__name__)


class RfpTicketNotFoundError(LookupError):
    """Raised when a ticket_id does not exist."""


class RfpSectionNotFoundError(LookupError):
    """Raised when a department section row does not exist."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_ticket_id() -> str:
    return str(uuid4())


def create_ticket_analyzing(
    session: Session,
    *,
    ticket_id: str | None = None,
    source_pdf_path: str | None = None,
    source_pdf_sha256: str | None = None,
) -> RfpTicket:
    """Insert a new ticket in ``analyzing`` status (POST /rfp/tickets)."""
    row = RfpTicket(
        ticket_id=ticket_id or new_ticket_id(),
        status=STATUS_ANALYZING,
        source_pdf_path=source_pdf_path,
        source_pdf_sha256=source_pdf_sha256,
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_ticket(session: Session, ticket_id: str) -> RfpTicket | None:
    return session.get(RfpTicket, ticket_id)


def get_ticket_or_raise(session: Session, ticket_id: str) -> RfpTicket:
    row = get_ticket(session, ticket_id)
    if row is None:
        raise RfpTicketNotFoundError(f"RFP ticket not found: {ticket_id}")
    return row


def list_tickets(
    session: Session,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[RfpTicket]:
    query = select(RfpTicket)
    if status is not None:
        query = query.where(RfpTicket.status == status)
    query = query.order_by(RfpTicket.created_at.desc()).offset(offset).limit(limit)
    return list(session.exec(query).all())


def list_sections(session: Session, ticket_id: str) -> list[RfpDepartmentSection]:
    return list(
        session.exec(
            select(RfpDepartmentSection)
            .where(RfpDepartmentSection.ticket_id == ticket_id)
            .order_by(RfpDepartmentSection.department_id)
        ).all()
    )


def get_section(
    session: Session,
    *,
    ticket_id: str,
    department_id: str,
) -> RfpDepartmentSection | None:
    return session.exec(
        select(RfpDepartmentSection).where(
            RfpDepartmentSection.ticket_id == ticket_id,
            RfpDepartmentSection.department_id == department_id,
        )
    ).first()


def get_section_or_raise(
    session: Session,
    *,
    ticket_id: str,
    department_id: str,
) -> RfpDepartmentSection:
    row = get_section(session, ticket_id=ticket_id, department_id=department_id)
    if row is None:
        raise RfpSectionNotFoundError(
            f"RFP section not found: ticket={ticket_id} department={department_id}"
        )
    return row


def upsert_department_section(
    session: Session,
    *,
    ticket_id: str,
    department_id: str,
    key_aspects: list[str],
) -> RfpDepartmentSection:
    existing = session.exec(
        select(RfpDepartmentSection).where(
            RfpDepartmentSection.ticket_id == ticket_id,
            RfpDepartmentSection.department_id == department_id,
        )
    ).first()
    if existing is not None:
        existing.key_aspects = key_aspects
        existing.updated_at = _utc_now()
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    row = RfpDepartmentSection(
        ticket_id=ticket_id,
        department_id=department_id,
        key_aspects=key_aspects,
        draft_status=DRAFT_STATUS_PENDING,
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_department_section(
    session: Session,
    *,
    ticket_id: str,
    department_id: str,
    draft_content: str | None = None,
    evaluation_results: dict[str, Any] | None = None,
    draft_status: str | None = None,
    approval_status: str | None = None,
    approver: str | None = None,
    approved_at: datetime | None = None,
    approval_comment: str | None = None,
    clear_approval_fields: bool = False,
) -> RfpDepartmentSection:
    """Update P2/P3 fields on an existing department section row."""
    row = session.exec(
        select(RfpDepartmentSection).where(
            RfpDepartmentSection.ticket_id == ticket_id,
            RfpDepartmentSection.department_id == department_id,
        )
    ).first()
    if row is None:
        raise LookupError(
            f"RFP section not found: ticket={ticket_id} department={department_id}"
        )
    if draft_content is not None:
        row.draft_content = draft_content
    if evaluation_results is not None:
        row.evaluation_results = evaluation_results
    if draft_status is not None:
        row.draft_status = draft_status
    if clear_approval_fields:
        row.approval_status = None
        row.approver = None
        row.approved_at = None
        row.approval_comment = None
    else:
        if approval_status is not None:
            row.approval_status = approval_status
        if approver is not None:
            row.approver = approver
        if approved_at is not None:
            row.approved_at = approved_at
        if approval_comment is not None:
            row.approval_comment = approval_comment
    row.updated_at = _utc_now()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def append_trace_event(
    session: Session,
    *,
    ticket_id: str,
    node: str,
    payload: dict[str, Any] | None = None,
) -> RfpTraceEvent:
    event_payload = {"node": node, **(payload or {})}
    row = RfpTraceEvent(
        ticket_id=ticket_id,
        node=node,
        payload=event_payload,
        created_at=_utc_now(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_ticket(
    session: Session,
    ticket_id: str,
    **fields: Any,
) -> RfpTicket:
    row = get_ticket_or_raise(session, ticket_id)
    for key, value in fields.items():
        if key == "metadata":
            setattr(row, "metadata_json", value)
        elif hasattr(row, key):
            setattr(row, key, value)
    row.updated_at = _utc_now()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_trace_events(
    session: Session,
    ticket_id: str,
    *,
    limit: int = 500,
) -> list[RfpTraceEventResponse]:
    """Return durable trace rows for a ticket (P1–P3 graph nodes)."""
    get_ticket_or_raise(session, ticket_id)
    rows = list(
        session.exec(
            select(RfpTraceEvent)
            .where(RfpTraceEvent.ticket_id == ticket_id)
            .order_by(RfpTraceEvent.created_at, RfpTraceEvent.id)
            .limit(limit)
        ).all()
    )
    return [
        RfpTraceEventResponse(
            id=row.id or 0,
            node=row.node,
            payload=dict(row.payload or {}),
            created_at=row.created_at,
        )
        for row in rows
    ]


def _build_ceo_approval_packet(
    row: RfpTicket,
    sections: list[RfpDepartmentSection],
) -> RfpCeoApprovalPacketResponse | None:
    if row.status != STATUS_AWAITING_CEO_APPROVAL:
        return None
    from data.pipelines.rfp_approval_packet import build_ceo_approval_packet

    approved_excerpts = {
        section.department_id: section.draft_content or ""
        for section in sections
        if section.approval_status == APPROVAL_STATUS_APPROVED
    }
    packet = build_ceo_approval_packet(
        ticket_id=row.ticket_id,
        metadata=dict(row.metadata_json or {}),
        requires_ceo_approval=bool(row.requires_ceo_approval),
        approved_excerpts=approved_excerpts,
        arbitration_resolutions=list(row.arbitration_resolutions or []),
        remaining_conflicts=list(row.conflicts or []),
    )
    return RfpCeoApprovalPacketResponse(**packet)


def _to_summary(row: RfpTicket) -> RfpTicketSummaryResponse:
    return RfpTicketSummaryResponse(
        ticket_id=row.ticket_id,
        status=row.status,
        status_label=status_label(row.status),
        metadata=dict(row.metadata_json or {}),
        departments_needed=list(row.departments_needed or []),
        requires_ceo_approval=bool(row.requires_ceo_approval),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_detail(row: RfpTicket, sections: list[RfpDepartmentSection]) -> RfpTicketDetailResponse:
    markdown = row.markdown_text or ""
    final_doc = row.final_document_markdown or ""
    return RfpTicketDetailResponse(
        ticket_id=row.ticket_id,
        status=row.status,
        status_label=status_label(row.status),
        metadata=dict(row.metadata_json or {}),
        departments_needed=list(row.departments_needed or []),
        requires_ceo_approval=bool(row.requires_ceo_approval),
        created_at=row.created_at,
        updated_at=row.updated_at,
        unmapped_topics=list(row.unmapped_topics or []),
        conflicts=list(row.conflicts or []),
        intake_summary=row.intake_summary,
        discard_reason=row.discard_reason,
        error_message=row.error_message,
        error_code=row.error_code,
        markdown_length=len(markdown),
        has_markdown=bool(markdown.strip()),
        has_final_document=bool(final_doc.strip()),
        final_document_length=len(final_doc),
        arbitration_exhausted=bool(row.arbitration_exhausted),
        arbitration_resolutions=list(row.arbitration_resolutions or []),
        ceo_approval_comment=row.ceo_approval_comment,
        ceo_approval_packet=_build_ceo_approval_packet(row, sections),
        sections=[
            RfpSectionResponse(
                department_id=section.department_id,
                department_label=department_label(section.department_id),
                department_owner=department_owner(section.department_id),
                key_aspects=list(section.key_aspects or []),
                draft_status=section.draft_status or DRAFT_STATUS_PENDING,
                draft_status_label=draft_status_label(section.draft_status),
                draft_content=section.draft_content,
                evaluation_results=section.evaluation_results,
                approval_status=section.approval_status,
                approval_status_label=approval_status_label(section.approval_status),
                approver=section.approver,
                approved_at=section.approved_at,
                approval_comment=section.approval_comment,
            )
            for section in sections
        ],
    )


def ticket_summary(session: Session, ticket_id: str) -> RfpTicketSummaryResponse:
    return _to_summary(get_ticket_or_raise(session, ticket_id))


def ticket_detail(session: Session, ticket_id: str) -> RfpTicketDetailResponse:
    row = get_ticket_or_raise(session, ticket_id)
    sections = list_sections(session, ticket_id)
    return _to_detail(row, sections)


def list_ticket_summaries(
    session: Session,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[RfpTicketSummaryResponse]:
    return [_to_summary(row) for row in list_tickets(session, status=status, limit=limit, offset=offset)]


def delete_ticket(session: Session, ticket_id: str) -> None:
    """Remove ticket rows and stored intake PDF artifacts."""
    row = get_ticket(session, ticket_id)
    if row is None:
        raise RfpTicketNotFoundError(f"RFP ticket not found: {ticket_id}")

    for event in session.exec(
        select(RfpTraceEvent).where(RfpTraceEvent.ticket_id == ticket_id)
    ):
        session.delete(event)
    for section in session.exec(
        select(RfpDepartmentSection).where(RfpDepartmentSection.ticket_id == ticket_id)
    ):
        session.delete(section)
    session.delete(row)
    session.commit()

    try:
        from rfp.intake_service import delete_ticket_files

        delete_ticket_files(ticket_id)
    except Exception:  # noqa: BLE001 — DB delete already committed
        logger.exception("Could not remove stored PDF files for ticket %s", ticket_id)


__all__ = [
    "RfpTicketNotFoundError",
    "append_trace_event",
    "create_ticket_analyzing",
    "delete_ticket",
    "get_ticket",
    "get_ticket_or_raise",
    "list_sections",
    "list_ticket_summaries",
    "list_tickets",
    "list_trace_events",
    "new_ticket_id",
    "ticket_detail",
    "ticket_summary",
    "update_department_section",
    "update_ticket",
    "upsert_department_section",
]
