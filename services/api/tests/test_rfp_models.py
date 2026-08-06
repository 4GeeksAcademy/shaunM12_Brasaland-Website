"""RFP data layer tests (context-27 Part 1 — Phase 1 gate)."""

from __future__ import annotations

import config
import pytest
from sqlmodel import Session

from database import get_engine
from rfp.constants import (
    DEPARTMENT_MARKETING,
    DEPARTMENT_OPERATIONS,
    STATUS_ANALYZING,
    STATUS_INTAKE_COMPLETE,
)
from rfp.models import ensure_rfp_schema
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


def test_phase0_dependency_imports():
    import langgraph  # noqa: F401
    import langgraph.checkpoint.sqlite  # noqa: F401
    import markitdown  # noqa: F401
    import readability  # py-readability-metrics  # noqa: F401
