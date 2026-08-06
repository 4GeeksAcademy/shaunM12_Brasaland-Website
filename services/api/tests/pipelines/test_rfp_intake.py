"""RFP intake graph evals — seed PDFs + Postgres persistence (context-27 Phase 5)."""

from __future__ import annotations

import config
import pytest
from sqlmodel import Session, select

from database import get_engine
from rfp.constants import (
    DEPARTMENT_TRAINING,
    ERROR_PDF_CONVERSION_FAILED,
    SEED_PDF_FILES,
    STATUS_DISCARDED,
    STATUS_FAILED,
    STATUS_INTAKE_COMPLETE,
    department_owner,
)
from rfp.graph import reset_graph_cache
from rfp.intake_service import create_ticket_from_pdf, seed_asset_path
from rfp.models import RfpTraceEvent, ensure_rfp_schema
from rfp.repository import ticket_detail

pytestmark = pytest.mark.skipif(
    not config.DATABASE_URL,
    reason="DATABASE_URL not set — RFP intake tests require PostgreSQL",
)


@pytest.fixture(autouse=True)
def _rfp_graph_env(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("RFP_CHECKPOINT_DB_PATH", str(tmp_path / "rfp_checkpoints.db"))
    reset_graph_cache()
    yield
    reset_graph_cache()


@pytest.fixture(scope="module", autouse=True)
def _ensure_schema() -> None:
    with Session(get_engine()) as session:
        ensure_rfp_schema(session)


def test_graph_compiles_with_sqlite_checkpointer():
    from rfp.graph import get_compiled_graph

    assert get_compiled_graph() is not None


def test_seed1_sunset_bay_intake_complete():
    with Session(get_engine()) as session:
        ticket_id = create_ticket_from_pdf(
            session, seed_asset_path(SEED_PDF_FILES[0])
        )
        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_INTAKE_COMPLETE
        assert detail.requires_ceo_approval is True
        assert detail.has_markdown is True
        assert len(detail.sections) == 4
        dept_ids = {section.department_id for section in detail.sections}
        assert DEPARTMENT_TRAINING in dept_ids
        assert all(section.key_aspects for section in detail.sections)
        assert all(section.department_owner for section in detail.sections)
        assert detail.sections[0].department_owner == department_owner(
            detail.sections[0].department_id
        )
        assert detail.metadata.get("readability_scores")


def test_seed2_andes_tech_three_departments_no_training():
    with Session(get_engine()) as session:
        ticket_id = create_ticket_from_pdf(
            session, seed_asset_path(SEED_PDF_FILES[1])
        )
        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_INTAKE_COMPLETE
        assert detail.requires_ceo_approval is False
        assert len(detail.sections) == 3
        dept_ids = {section.department_id for section in detail.sections}
        assert DEPARTMENT_TRAINING not in dept_ids


def test_seed3_franchise_discarded():
    with Session(get_engine()) as session:
        ticket_id = create_ticket_from_pdf(
            session, seed_asset_path(SEED_PDF_FILES[2])
        )
        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_DISCARDED
        assert detail.discard_reason
        assert detail.sections == []
        assert "readability_scores" in detail.metadata
        assert detail.has_markdown is True


def test_corrupt_pdf_failed(tmp_path, monkeypatch):
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"%PDF-1.4\nnot a valid pdf document")

    def _raise_conversion(_path):
        raise ValueError("PDF conversion produced empty text")

    monkeypatch.setattr(
        "data.pipelines.rfp_intake.convert_pdf_to_markdown",
        _raise_conversion,
    )

    with Session(get_engine()) as session:
        ticket_id = create_ticket_from_pdf(session, corrupt_pdf)
        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_FAILED
        assert detail.error_code == ERROR_PDF_CONVERSION_FAILED
        assert detail.error_message
        assert detail.has_markdown is False


def test_seed1_persists_trace_events_and_readability():
    with Session(get_engine()) as session:
        ticket_id = create_ticket_from_pdf(
            session, seed_asset_path(SEED_PDF_FILES[0])
        )
        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_INTAKE_COMPLETE
        assert detail.has_markdown is True
        assert detail.metadata.get("readability_scores")
        assert detail.status_label == "Intake complete"

        events = list(
            session.exec(
                select(RfpTraceEvent).where(RfpTraceEvent.ticket_id == ticket_id)
            ).all()
        )
        nodes = {event.node for event in events}
        assert "convert_pdf" in nodes
        assert "readability" in nodes
        assert "classify" in nodes
        assert "synthesize" in nodes
        assert len(events) >= 5


def test_convert_pdf_produces_markdown():
    from data.pipelines.rfp_intake import convert_pdf_to_markdown

    text = convert_pdf_to_markdown(seed_asset_path(SEED_PDF_FILES[0]))
    assert "Sunset Bay" in text
