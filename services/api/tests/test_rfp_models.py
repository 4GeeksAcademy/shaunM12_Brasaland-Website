"""RFP data layer tests (context-27 Part 1 — Phase 1 gate)."""

from __future__ import annotations

import config
import pytest
from sqlmodel import Session, select

from database import get_engine
from rfp.constants import (
    DEPARTMENT_MARKETING,
    DEPARTMENT_OPERATIONS,
    DRAFT_STATUS_EVALUATING,
    DRAFT_STATUS_PENDING,
    STATUS_ANALYZING,
    STATUS_INTAKE_COMPLETE,
)
from rfp.models import RfpDepartmentSection, ensure_rfp_schema
from rfp.repository import (
    append_trace_event,
    create_ticket_analyzing,
    get_ticket,
    ticket_detail,
    update_ticket,
    upsert_department_section,
)

pytestmark = pytest.mark.skipif(
    not config.DATABASE_URL,
    reason="DATABASE_URL not set — RFP tests require PostgreSQL",
)


@pytest.fixture(scope="module", autouse=True)
def _ensure_schema() -> None:
    with Session(get_engine()) as session:
        ensure_rfp_schema(session)


def test_create_ticket_analyzing():
    with Session(get_engine()) as session:
        row = create_ticket_analyzing(
            session,
            source_pdf_path="data/raw/intakes/test/source.pdf",
            source_pdf_sha256="abc123",
        )
        assert row.ticket_id
        assert row.status == STATUS_ANALYZING
        assert row.source_pdf_sha256 == "abc123"

        fetched = get_ticket(session, row.ticket_id)
        assert fetched is not None
        assert fetched.status == STATUS_ANALYZING


def test_upsert_department_sections_and_trace():
    with Session(get_engine()) as session:
        ticket = create_ticket_analyzing(session)
        upsert_department_section(
            session,
            ticket_id=ticket.ticket_id,
            department_id=DEPARTMENT_MARKETING,
            key_aspects=["Brand co-marketing", "Exclusivity terms"],
        )
        upsert_department_section(
            session,
            ticket_id=ticket.ticket_id,
            department_id=DEPARTMENT_OPERATIONS,
            key_aspects=["Staffing plan"],
        )
        append_trace_event(
            session,
            ticket_id=ticket.ticket_id,
            node="classify",
            payload={"departments_needed": [DEPARTMENT_MARKETING, DEPARTMENT_OPERATIONS]},
        )
        update_ticket(
            session,
            ticket.ticket_id,
            status=STATUS_INTAKE_COMPLETE,
            metadata={"client_name": "Sunset Bay Resorts, LLC"},
            departments_needed=[DEPARTMENT_MARKETING, DEPARTMENT_OPERATIONS],
            requires_ceo_approval=True,
            intake_summary="Routing complete.",
            markdown_text="# RFP\n",
        )

        detail = ticket_detail(session, ticket.ticket_id)
        assert detail.status == STATUS_INTAKE_COMPLETE
        assert detail.status_label == "Intake complete"
        assert detail.metadata["client_name"] == "Sunset Bay Resorts, LLC"
        assert detail.requires_ceo_approval is True
        assert detail.markdown_length == len("# RFP\n")
        assert detail.has_markdown is True
        assert len(detail.sections) == 2
        assert detail.sections[0].key_aspects
        assert detail.sections[0].draft_status == DRAFT_STATUS_PENDING
        assert detail.sections[0].draft_status_label == "Pending"


def test_draft_status_column_migration_and_update():
    """Part 2 Phase 0 — draft_status persisted and returned on GET detail."""
    with Session(get_engine()) as session:
        ticket = create_ticket_analyzing(session)
        section = upsert_department_section(
            session,
            ticket_id=ticket.ticket_id,
            department_id=DEPARTMENT_MARKETING,
            key_aspects=["Brand alignment"],
        )
        assert section.draft_status == DRAFT_STATUS_PENDING

        row = session.exec(
            select(RfpDepartmentSection).where(
                RfpDepartmentSection.ticket_id == ticket.ticket_id,
                RfpDepartmentSection.department_id == DEPARTMENT_MARKETING,
            )
        ).one()
        row.draft_status = DRAFT_STATUS_EVALUATING
        session.add(row)
        session.commit()

        detail = ticket_detail(session, ticket.ticket_id)
        marketing = next(
            s for s in detail.sections if s.department_id == DEPARTMENT_MARKETING
        )
        assert marketing.draft_status == DRAFT_STATUS_EVALUATING
        assert marketing.draft_status_label == "Evaluating"


def test_phase0_dependency_imports():
    import langgraph  # noqa: F401
    import langgraph.checkpoint.sqlite  # noqa: F401
    import markitdown  # noqa: F401
    import readability  # py-readability-metrics  # noqa: F401


def test_p3_phase0_final_document_and_approval_fields():
    """Part 3 Phase 0 — final doc columns + approval metadata on GET detail."""
    from datetime import datetime, timezone

    from rfp.constants import (
        APPROVAL_STATUS_APPROVED,
        STATUS_COMPLETED,
    )
    from rfp.repository import update_department_section

    with Session(get_engine()) as session:
        ticket = create_ticket_analyzing(session)
        upsert_department_section(
            session,
            ticket_id=ticket.ticket_id,
            department_id=DEPARTMENT_MARKETING,
            key_aspects=["Brand alignment"],
        )
        final_text = "# Brasaland Proposal\n\nApproved sections merged."
        approved_at = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
        update_ticket(
            session,
            ticket.ticket_id,
            status=STATUS_COMPLETED,
            final_document_markdown=final_text,
            final_document_generated_at=approved_at,
            arbitration_exhausted=False,
        )
        update_department_section(
            session,
            ticket_id=ticket.ticket_id,
            department_id=DEPARTMENT_MARKETING,
            approval_status=APPROVAL_STATUS_APPROVED,
            approver="Camila Ospina",
            approved_at=approved_at,
        )

        detail = ticket_detail(session, ticket.ticket_id)
        assert detail.status == STATUS_COMPLETED
        assert detail.status_label == "Done"
        assert detail.has_final_document is True
        assert detail.final_document_length == len(final_text)
        assert detail.arbitration_exhausted is False

        marketing = detail.sections[0]
        assert marketing.approval_status == APPROVAL_STATUS_APPROVED
        assert marketing.approval_status_label == "Approved"
        assert marketing.approver == "Camila Ospina"
        assert marketing.approved_at is not None
        assert marketing.approved_at.replace(tzinfo=timezone.utc) == approved_at


def test_p3_status_constants_and_approval_labels():
    from rfp.constants import (
        APPROVAL_STATUS_AWAITING_HUMAN,
        APPROVAL_STATUS_LABELS,
        APPROVAL_DECISION_VALUES,
        CEO_DECISION_VALUES,
        STATUS_AWAITING_CEO_APPROVAL,
        STATUS_AWAITING_DEPARTMENT_APPROVAL,
        STATUS_LABELS,
        STATUS_VALUES,
        approval_status_label,
        status_label,
    )

    assert STATUS_AWAITING_DEPARTMENT_APPROVAL in STATUS_VALUES
    assert STATUS_AWAITING_CEO_APPROVAL in STATUS_VALUES
    assert status_label(STATUS_AWAITING_DEPARTMENT_APPROVAL) == "Awaiting department approval"
    assert approval_status_label(APPROVAL_STATUS_AWAITING_HUMAN) == "Awaiting human approval"
    assert APPROVAL_STATUS_AWAITING_HUMAN in APPROVAL_STATUS_LABELS
    assert "approve" in APPROVAL_DECISION_VALUES
    assert "reject" in CEO_DECISION_VALUES
