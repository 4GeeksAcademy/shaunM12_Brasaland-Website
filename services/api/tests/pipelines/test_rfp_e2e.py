"""RFP Part 3 end-to-end tests — P1 intake → P2 draft → P3 approval → completed (context-27 P3 Phase 5)."""

from __future__ import annotations

import config
import pytest
from sqlmodel import Session, select

from database import get_engine
from rfp.approval_service import (
    get_final_document,
    run_approval_for_ticket,
    submit_ceo_decision,
    submit_department_decision,
)
from rfp.constants import (
    APPROVAL_DECISION_APPROVE,
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_AWAITING_HUMAN,
    CEO_DECISION_APPROVE,
    SEED_PDF_FILES,
    STATUS_AWAITING_CEO_APPROVAL,
    STATUS_AWAITING_DEPARTMENT_APPROVAL,
    STATUS_COMPLETED,
    STATUS_INTAKE_COMPLETE,
    STATUS_WAITING_FOR_APPROVAL,
)
from rfp.draft_service import run_generation_for_ticket
from rfp.graph import reset_graph_cache
from rfp.intake_service import create_ticket_from_pdf, seed_asset_path
from rfp.models import RfpTraceEvent, ensure_rfp_schema
from rfp.repository import ticket_detail

pytestmark = pytest.mark.skipif(
    not config.DATABASE_URL,
    reason="DATABASE_URL not set — RFP E2E tests require PostgreSQL",
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

P1_TRACE_NODES = frozenset({"convert_pdf", "readability", "classify", "synthesize"})
P2_TRACE_NODES = frozenset({"draft_start", "generate_eval_dept", "generation_finalize"})
P3_TRACE_NODES = frozenset(
    {
        "approval_start",
        "prepare_approval_packet",
        "dept_approval_interrupt",
        "mark_dept_approved",
        "ultimate_document_synthesizer",
        "approval_finalize",
    }
)


@pytest.fixture(autouse=True)
def _rfp_graph_env(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("RFP_CHECKPOINT_DB_PATH", str(tmp_path / "rfp_e2e_checkpoints.db"))
    reset_graph_cache()
    yield
    reset_graph_cache()


@pytest.fixture(scope="module", autouse=True)
def _ensure_schema() -> None:
    with Session(get_engine()) as session:
        ensure_rfp_schema(session)


@pytest.fixture(autouse=True)
def _mock_generation_llm(monkeypatch: pytest.MonkeyPatch):
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


def _trace_nodes(session: Session, ticket_id: str) -> set[str]:
    events = list(
        session.exec(
            select(RfpTraceEvent).where(RfpTraceEvent.ticket_id == ticket_id)
        ).all()
    )
    return {event.node for event in events}


def _run_through_generation(session: Session, seed_index: int) -> str:
    ticket_id = create_ticket_from_pdf(
        session,
        seed_asset_path(SEED_PDF_FILES[seed_index]),
    )
    detail = ticket_detail(session, ticket_id)
    assert detail.status == STATUS_INTAKE_COMPLETE

    run_generation_for_ticket(session, ticket_id)
    detail = ticket_detail(session, ticket_id)
    assert detail.status == STATUS_WAITING_FOR_APPROVAL
    for section in detail.sections:
        assert section.draft_content
        assert section.evaluation_results
    return ticket_id


def _start_approval(session: Session, ticket_id: str) -> None:
    run_approval_for_ticket(session, ticket_id)
    detail = ticket_detail(session, ticket_id)
    assert detail.status == STATUS_AWAITING_DEPARTMENT_APPROVAL
    for section in detail.sections:
        assert section.approval_status == APPROVAL_STATUS_AWAITING_HUMAN


def _approve_all_departments(session: Session, ticket_id: str) -> None:
    detail = ticket_detail(session, ticket_id)
    for section in detail.sections:
        if section.approval_status != APPROVAL_STATUS_AWAITING_HUMAN:
            continue
        submit_department_decision(
            session,
            ticket_id=ticket_id,
            department_id=section.department_id,
            decision=APPROVAL_DECISION_APPROVE,
            approver="E2E Tester",
        )


def test_e2e_seed2_intake_draft_approval_completed():
    """Seed #2 (no CEO): full pipeline → completed + final document."""
    with Session(get_engine()) as session:
        ticket_id = _run_through_generation(session, seed_index=1)
        _start_approval(session, ticket_id)
        _approve_all_departments(session, ticket_id)

        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_COMPLETED
        assert detail.requires_ceo_approval is False
        assert detail.has_final_document is True
        assert detail.final_document_length > 0
        for section in detail.sections:
            assert section.approval_status == APPROVAL_STATUS_APPROVED

        final_doc = get_final_document(session, ticket_id)
        assert len(final_doc["final_document_markdown"]) > 0
        assert final_doc["generated_at"] is not None


def test_e2e_seed1_ceo_path_completed():
    """Seed #1 (> $50k): all dept approvals → CEO gate → completed."""
    with Session(get_engine()) as session:
        ticket_id = _run_through_generation(session, seed_index=0)
        detail = ticket_detail(session, ticket_id)
        assert detail.requires_ceo_approval is True
        assert len(detail.sections) == 4

        _start_approval(session, ticket_id)
        _approve_all_departments(session, ticket_id)

        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_AWAITING_CEO_APPROVAL

        submit_ceo_decision(
            session,
            ticket_id=ticket_id,
            decision=CEO_DECISION_APPROVE,
            approver="Mariana Restrepo",
        )

        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_COMPLETED
        assert detail.has_final_document is True


def test_e2e_parallel_approve_ops_while_marketing_waiting():
    """Approve operations while marketing remains awaiting_human — ticket not completed."""
    with Session(get_engine()) as session:
        ticket_id = _run_through_generation(session, seed_index=1)
        _start_approval(session, ticket_id)

        submit_department_decision(
            session,
            ticket_id=ticket_id,
            department_id="operations",
            decision=APPROVAL_DECISION_APPROVE,
            approver="E2E Tester",
        )

        detail = ticket_detail(session, ticket_id)
        assert detail.status != STATUS_COMPLETED
        by_dept = {section.department_id: section for section in detail.sections}
        assert by_dept["operations"].approval_status == APPROVAL_STATUS_APPROVED
        assert by_dept["marketing"].approval_status == APPROVAL_STATUS_AWAITING_HUMAN


def test_e2e_p1_p2_p3_trace_chain():
    """Trace spans intake, generation, and approval nodes for one ticket."""
    with Session(get_engine()) as session:
        ticket_id = _run_through_generation(session, seed_index=1)
        _start_approval(session, ticket_id)
        _approve_all_departments(session, ticket_id)

        nodes = _trace_nodes(session, ticket_id)
        assert P1_TRACE_NODES.issubset(nodes), f"missing P1 nodes; got {nodes}"
        assert P2_TRACE_NODES.issubset(nodes), f"missing P2 nodes; got {nodes}"
        assert P3_TRACE_NODES.issubset(nodes), f"missing P3 nodes; got {nodes}"

        events = list(
            session.exec(
                select(RfpTraceEvent).where(RfpTraceEvent.ticket_id == ticket_id)
            ).all()
        )
        for sample_node in ("convert_pdf", "draft_start", "dept_approval_interrupt"):
            payload = next(
                dict(event.payload or {}) for event in events if event.node == sample_node
            )
            assert payload.get("agent")
            assert isinstance(payload.get("input"), dict)
            assert isinstance(payload.get("output"), dict)
            assert payload.get("timestamp", "").endswith("Z")

        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_COMPLETED


def test_e2e_concurrent_tickets_isolated_checkpoints():
    """Two tickets share one checkpoint DB but distinct thread_id namespaces."""
    with Session(get_engine()) as session:
        ticket_a = _run_through_generation(session, seed_index=1)
        ticket_b = _run_through_generation(session, seed_index=1)
        assert ticket_a != ticket_b

        _start_approval(session, ticket_a)
        _start_approval(session, ticket_b)

        submit_department_decision(
            session,
            ticket_id=ticket_a,
            department_id="operations",
            decision=APPROVAL_DECISION_APPROVE,
            approver="Concurrent Test",
        )

        detail_a = ticket_detail(session, ticket_a)
        detail_b = ticket_detail(session, ticket_b)

        by_a = {s.department_id: s for s in detail_a.sections}
        by_b = {s.department_id: s for s in detail_b.sections}

        assert by_a["operations"].approval_status == APPROVAL_STATUS_APPROVED
        assert by_b["operations"].approval_status == APPROVAL_STATUS_AWAITING_HUMAN
        assert by_b["marketing"].approval_status == APPROVAL_STATUS_AWAITING_HUMAN
        assert detail_a.status != STATUS_COMPLETED
        assert detail_b.status == STATUS_AWAITING_DEPARTMENT_APPROVAL
