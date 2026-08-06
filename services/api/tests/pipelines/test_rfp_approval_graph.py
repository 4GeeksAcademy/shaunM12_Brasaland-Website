"""RFP Part 3 LangGraph integration tests (context-27 P3 Phase 2 gate)."""

from __future__ import annotations

import config
import pytest
from sqlmodel import Session, select

from database import get_engine
from data.pipelines.rfp_approval_packet import (
    ApprovalResponseError,
    build_evaluation_summary,
    validate_ceo_response,
    validate_human_response,
)
from rfp.approval_service import run_approval_for_ticket, submit_department_decision
from rfp.constants import (
    APPROVAL_DECISION_APPROVE,
    APPROVAL_STATUS_AWAITING_HUMAN,
    APPROVAL_STATUS_APPROVED,
    DEPARTMENT_MARKETING,
    DEPARTMENT_OPERATIONS,
    DRAFT_STATUS_NEEDS_HUMAN_REVIEW,
    DRAFT_STATUS_PASSED,
    SEED_PDF_FILES,
    STATUS_AWAITING_DEPARTMENT_APPROVAL,
    STATUS_COMPLETED,
    STATUS_INTAKE_COMPLETE,
    STATUS_WAITING_FOR_APPROVAL,
)
from rfp.draft_service import run_generation_for_ticket
from rfp.graph import reset_graph_cache
from rfp.intake_service import create_ticket_from_pdf, seed_asset_path
from rfp.models import RfpTraceEvent, ensure_rfp_schema
from rfp.repository import ticket_detail, update_ticket

pytestmark = pytest.mark.skipif(
    not config.DATABASE_URL,
    reason="DATABASE_URL not set — RFP approval graph tests require PostgreSQL",
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
    monkeypatch.setenv("RFP_CHECKPOINT_DB_PATH", str(tmp_path / "rfp_approval_checkpoints.db"))
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


def test_merged_graph_compiles_with_approval_nodes():
    from rfp.graph import get_compiled_graph

    graph = get_compiled_graph()
    assert graph is not None


def test_validate_human_response_accepts_approve():
    result = validate_human_response(
        {
            "kind": "dept_approval",
            "department_id": "marketing",
            "decision": "approve",
            "approver": "Camila Ospina",
        },
        expected_department_id="marketing",
    )
    assert result["decision"] == "approve"
    assert result["approver"] == "Camila Ospina"


def test_validate_human_response_rejects_wrong_department():
    with pytest.raises(ApprovalResponseError, match="Department mismatch"):
        validate_human_response(
            {"department_id": "operations", "decision": "approve"},
            expected_department_id="marketing",
        )


def test_validate_ceo_response_accepts_approve():
    result = validate_ceo_response({"kind": "ceo_approval", "decision": "approve"})
    assert result["decision"] == "approve"


def test_build_evaluation_summary_from_latest():
    summary = build_evaluation_summary(
        {
            "latest": {
                "iteration": 2,
                "overall_passed": False,
                "needs_human_review": True,
                "readability": {"passed": True},
                "relevance": {"passed": False, "missing_topics": ["staffing"]},
                "compliance": {"passed": True, "failures": []},
            }
        }
    )
    assert summary["needs_human_review"] is True
    assert summary["missing_topics"] == ["staffing"]


def test_approval_invoke_reaches_dept_interrupts():
    """Phase 2 gate — fixture ticket after P2 reaches per-dept awaiting_human interrupts."""
    with Session(get_engine()) as session:
        ticket_id = create_ticket_from_pdf(
            session,
            seed_asset_path(SEED_PDF_FILES[1]),
        )
        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_INTAKE_COMPLETE

        run_generation_for_ticket(session, ticket_id)
        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_WAITING_FOR_APPROVAL

        run_approval_for_ticket(session, ticket_id)
        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_AWAITING_DEPARTMENT_APPROVAL
        assert len(detail.sections) >= 1
        for section in detail.sections:
            assert section.approval_status == APPROVAL_STATUS_AWAITING_HUMAN
            assert section.draft_content
            assert section.draft_status in (
                DRAFT_STATUS_PASSED,
                DRAFT_STATUS_NEEDS_HUMAN_REVIEW,
            )


def _count_trace_nodes(session: Session, ticket_id: str, node: str) -> int:
    events = list(
        session.exec(
            select(RfpTraceEvent).where(RfpTraceEvent.ticket_id == ticket_id)
        ).all()
    )
    return sum(1 for event in events if event.node == node)


def _assert_trace_envelope(payload: dict) -> None:
    assert payload.get("agent")
    assert isinstance(payload.get("input"), dict)
    assert isinstance(payload.get("output"), dict)
    assert payload.get("timestamp", "").endswith("Z")


def test_resume_rfp_approval_does_not_rerun_intake():
    """Resume from dept interrupt must not re-invoke P1 convert_pdf."""
    with Session(get_engine()) as session:
        ticket_id = create_ticket_from_pdf(
            session,
            seed_asset_path(SEED_PDF_FILES[1]),
        )
        run_generation_for_ticket(session, ticket_id)
        run_approval_for_ticket(session, ticket_id)

        convert_count_before = _count_trace_nodes(session, ticket_id, "convert_pdf")
        assert convert_count_before == 1

        detail = ticket_detail(session, ticket_id)
        target = next(
            s.department_id
            for s in detail.sections
            if s.approval_status == APPROVAL_STATUS_AWAITING_HUMAN
        )

        submit_department_decision(
            session,
            ticket_id=ticket_id,
            department_id=target,
            decision=APPROVAL_DECISION_APPROVE,
            approver="Resume Test",
        )

        convert_count_after = _count_trace_nodes(session, ticket_id, "convert_pdf")
        assert convert_count_after == convert_count_before

        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_AWAITING_DEPARTMENT_APPROVAL
        approved = [s for s in detail.sections if s.approval_status == APPROVAL_STATUS_APPROVED]
        assert len(approved) == 1


def test_arbitration_node_resolves_injected_conflicts():
    """Graph integration — injected intake conflict triggers rule-based arbitration_node."""
    injected_conflict = {
        "field": "deadline",
        "claims": [
            {"department_id": DEPARTMENT_MARKETING, "value": "2026-09-01"},
            {"department_id": DEPARTMENT_OPERATIONS, "value": "2026-09-15"},
        ],
    }

    with Session(get_engine()) as session:
        ticket_id = create_ticket_from_pdf(
            session,
            seed_asset_path(SEED_PDF_FILES[1]),
        )
        run_generation_for_ticket(session, ticket_id)
        update_ticket(session, ticket_id, conflicts=[injected_conflict])

        run_approval_for_ticket(session, ticket_id)
        detail = ticket_detail(session, ticket_id)
        for section in detail.sections:
            submit_department_decision(
                session,
                ticket_id=ticket_id,
                department_id=section.department_id,
                decision=APPROVAL_DECISION_APPROVE,
                approver="Arbitration Test",
            )

        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_COMPLETED
        assert len(detail.arbitration_resolutions) >= 1
        assert detail.arbitration_resolutions[0]["winning_department_id"] == DEPARTMENT_OPERATIONS

        events = list(
            session.exec(
                select(RfpTraceEvent).where(RfpTraceEvent.ticket_id == ticket_id)
            ).all()
        )
        nodes = {event.node for event in events}
        assert "detect_conflicts" in nodes
        assert "arbitration_node" in nodes

        arbitration_payload = next(
            dict(event.payload or {}) for event in events if event.node == "arbitration_node"
        )
        _assert_trace_envelope(arbitration_payload)
        assert arbitration_payload["agent"] == "arbitration_node"
        assert arbitration_payload["output"]["resolutions_count"] >= 1
