"""SQLModel ORM tables for Milestone 9 RFP workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, Index, UniqueConstraint, inspect
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Session, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_list_column():
    return Field(default_factory=list, sa_column=Column(JSONB))


class RfpTicket(SQLModel, table=True):
    """One uploaded RFP document and its workflow state."""

    __tablename__ = "rfp_tickets"

    ticket_id: str = Field(primary_key=True, max_length=36)
    status: str = Field(index=True, default="analyzing", max_length=32)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSONB, nullable=False),
    )
    departments_needed: list[str] = _json_list_column()
    unmapped_topics: list[str] = _json_list_column()
    conflicts: list[dict[str, Any]] = _json_list_column()
    intake_summary: str | None = None
    requires_ceo_approval: bool = Field(default=False, index=True)
    markdown_text: str | None = None
    source_pdf_path: str | None = None
    source_pdf_sha256: str | None = Field(default=None, max_length=64)
    discard_reason: str | None = None
    error_message: str | None = None
    error_code: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=_utc_now, index=True)
    updated_at: datetime = Field(default_factory=_utc_now)


class RfpDepartmentSection(SQLModel, table=True):
    """Per-department routing (P1) and draft/approval (P2/P3)."""

    __tablename__ = "rfp_department_sections"
    __table_args__ = (
        UniqueConstraint("ticket_id", "department_id", name="uq_rfp_section_ticket_dept"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="rfp_tickets.ticket_id", index=True, max_length=36)
    department_id: str = Field(index=True, max_length=32)
    key_aspects: list[str] = _json_list_column()
    draft_content: str | None = None
    evaluation_results: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    approval_status: str | None = Field(default=None, max_length=32)
    approver: str | None = Field(default=None, max_length=128)
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class RfpTraceEvent(SQLModel, table=True):
    """Durable append-only trace for RFP graph nodes (context-23 shape)."""

    __tablename__ = "rfp_trace_events"
    __table_args__ = (
        Index("ix_rfp_trace_events_ticket_created", "ticket_id", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="rfp_tickets.ticket_id", index=True, max_length=36)
    node: str = Field(index=True, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(default_factory=_utc_now, index=True)


def ensure_rfp_schema(session: Session) -> None:
    """Create RFP tables when missing (additive; no destructive migration)."""
    bind = session.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("rfp_tickets"):
        SQLModel.metadata.create_all(
            bind,
            tables=[
                RfpTicket.__table__,
                RfpDepartmentSection.__table__,
                RfpTraceEvent.__table__,
            ],
        )


__all__ = [
    "RfpDepartmentSection",
    "RfpTicket",
    "RfpTraceEvent",
    "ensure_rfp_schema",
]
