"""Persistence layer for RFP tickets, sections, and trace events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlmodel import Session, select

from .constants import STATUS_ANALYZING, department_label, department_owner, status_label
from .models import RfpDepartmentSection, RfpTicket, RfpTraceEvent
from .schemas import (
    RfpSectionResponse,
    RfpTicketDetailResponse,
    RfpTicketSummaryResponse,
)


class RfpTicketNotFoundError(LookupError):
    """Raised when a ticket_id does not exist."""


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
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
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
        sections=[
            RfpSectionResponse(
                department_id=section.department_id,
                department_label=department_label(section.department_id),
                department_owner=department_owner(section.department_id),
                key_aspects=list(section.key_aspects or []),
                draft_content=section.draft_content,
                evaluation_results=section.evaluation_results,
                approval_status=section.approval_status,
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


__all__ = [
    "RfpTicketNotFoundError",
    "append_trace_event",
    "create_ticket_analyzing",
    "get_ticket",
    "get_ticket_or_raise",
    "list_sections",
    "list_ticket_summaries",
    "list_tickets",
    "new_ticket_id",
    "ticket_detail",
    "ticket_summary",
    "update_ticket",
    "upsert_department_section",
]
