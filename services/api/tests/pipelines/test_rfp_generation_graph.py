"""RFP Part 2 LangGraph integration tests (context-27 P2 Phase 2 gate)."""

from __future__ import annotations

import config
import pytest
from sqlmodel import Session

from database import get_engine
from rfp.constants import (
    DRAFT_STATUS_NEEDS_HUMAN_REVIEW,
    DRAFT_STATUS_PASSED,
    SEED_PDF_FILES,
    STATUS_INTAKE_COMPLETE,
    STATUS_WAITING_FOR_APPROVAL,
)
from rfp.draft_service import run_generation_for_ticket
from rfp.graph import reset_graph_cache
from rfp.intake_service import create_ticket_from_pdf, seed_asset_path
from rfp.models import ensure_rfp_schema
from rfp.repository import ticket_detail

pytestmark = pytest.mark.skipif(
    not config.DATABASE_URL,
    reason="DATABASE_URL not set — RFP generation graph tests require PostgreSQL",
)

MOCK_COMPLIANT_DRAFT = """
Brasaland department proposal section for this RFP response.

Brand co-marketing and exclusivity terms are included in this proposal presentation.
Operational feasibility and staffing plan covers peak season operations with a clear
setup timeline and service cadence for weekly delivery.
Pricing and volume-based ingredient costs are quoted at $45,000 USD per year
(COP 180,000,000 at 1 USD = 4000 COP). Supplier lead times for contract volume
are 12 business days from contract signature.
New recipe or standard development time includes certification and rollout across
locations for training and quality standards.

We deliver consistent product quality, warm customer experience, and speed of
service without sacrificing quality. This offer is valid for 30 days from issuance.
"""


@pytest.fixture(autouse=True)
def _rfp_graph_env(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("RFP_CHECKPOINT_DB_PATH", str(tmp_path / "rfp_gen_checkpoints.db"))
    reset_graph_cache()
    yield
    reset_graph_cache()


@pytest.fixture(scope="module", autouse=True)
def _ensure_schema() -> None:
    with Session(get_engine()) as session:
        ensure_rfp_schema(session)


@pytest.fixture(autouse=True)
def _mock_generation_llm(monkeypatch: pytest.MonkeyPatch):
    """Return a compliant draft for every generator LLM call."""
    from data.pipelines import rfp_generation as gen

    monkeypatch.setattr(gen, "_generation_available", lambda: True)

    def _fake_chat_json(system: str, user: str) -> dict:
        if "missing_topics" in system:
            return {"missing_topics": []}
        return {}

    def _fake_chat_text(system: str, user: str) -> str:
        return MOCK_COMPLIANT_DRAFT

    monkeypatch.setattr(gen, "_chat_json", _fake_chat_json)
    monkeypatch.setattr(gen, "_chat_text", _fake_chat_text)


def test_merged_graph_compiles_with_generation_nodes():
    from rfp.graph import get_compiled_graph

    graph = get_compiled_graph()
    assert graph is not None


def test_generation_invoke_reaches_waiting_for_approval():
    """Phase 2 gate — fixture ticket after intake completes P2 to terminal status."""
    with Session(get_engine()) as session:
        ticket_id = create_ticket_from_pdf(
            session,
            seed_asset_path(SEED_PDF_FILES[1]),
        )
        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_INTAKE_COMPLETE
        assert len(detail.sections) == 3

        run_generation_for_ticket(session, ticket_id)

        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_WAITING_FOR_APPROVAL
        assert len(detail.sections) == 3
        for section in detail.sections:
            assert section.draft_content
            assert section.evaluation_results
            assert section.evaluation_results.get("latest")
            assert section.draft_status in (
                DRAFT_STATUS_PASSED,
                DRAFT_STATUS_NEEDS_HUMAN_REVIEW,
            )
            latest = section.evaluation_results["latest"]
            assert "readability" in latest
            assert "relevance" in latest
            assert "compliance" in latest


def test_generation_finalize_fails_when_departments_incomplete():
    """Pending placeholders must not satisfy finalize — all depts need terminal drafts."""
    from data.pipelines.rfp_generation_graph import _generation_finalize_node
    from rfp.constants import DRAFT_STATUS_PENDING, STATUS_FAILED, STATUS_WAITING_FOR_APPROVAL

    partial = _generation_finalize_node(
        {
            "departments_needed": ["marketing", "operations"],
            "department_drafts": {"marketing": "Draft body text."},
            "department_draft_statuses": {
                "marketing": "passed",
                "operations": DRAFT_STATUS_PENDING,
            },
        }
    )
    assert partial["status"] == STATUS_FAILED
    assert "operations" in partial["error_message"]

    complete = _generation_finalize_node(
        {
            "departments_needed": ["marketing", "operations"],
            "department_drafts": {
                "marketing": "Draft A.",
                "operations": "Draft B.",
            },
            "department_draft_statuses": {
                "marketing": "passed",
                "operations": "needs_human_review",
            },
        }
    )
    assert complete["status"] == STATUS_WAITING_FOR_APPROVAL


def test_generation_parallel_departments_isolated():
    """Each department section receives its own persisted draft row."""
    with Session(get_engine()) as session:
        ticket_id = create_ticket_from_pdf(
            session,
            seed_asset_path(SEED_PDF_FILES[1]),
        )
        run_generation_for_ticket(session, ticket_id)
        detail = ticket_detail(session, ticket_id)
        dept_ids = {section.department_id for section in detail.sections}
        assert len(dept_ids) == 3
        for section in detail.sections:
            assert section.draft_content == MOCK_COMPLIANT_DRAFT.strip()
