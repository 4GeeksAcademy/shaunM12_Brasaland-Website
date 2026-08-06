"""RFP Part 3 approval HTTP API tests (context-27 P3 Phase 3 gate)."""

from __future__ import annotations

import config
import pytest
from sqlmodel import Session

from database import get_engine
from rfp.approval_service import run_approval_for_ticket
from rfp.constants import (
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_AWAITING_HUMAN,
    APPROVAL_STATUS_REJECTED,
    SEED_PDF_FILES,
    STATUS_AWAITING_DEPARTMENT_APPROVAL,
    STATUS_COMPLETED,
    STATUS_INTAKE_COMPLETE,
    STATUS_WAITING_FOR_APPROVAL,
)
from rfp.draft_service import run_generation_for_ticket
from rfp.graph import reset_graph_cache
from rfp.intake_service import create_ticket_from_pdf, seed_asset_path
from rfp.models import ensure_rfp_schema
from rfp.repository import ticket_detail

pytestmark_db = pytest.mark.skipif(
    not config.DATABASE_URL,
    reason="DATABASE_URL not set — RFP approval API tests require PostgreSQL",
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


def _stub_generation_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GENERATION_BASE_URL", "http://gen.test/v1")
    monkeypatch.setenv("GENERATION_API_KEY", "test-key")
    monkeypatch.setenv("GENERATION_MODEL_ID", "test-model")
    monkeypatch.setattr(config, "GENERATION_BASE_URL", "http://gen.test/v1")
    monkeypatch.setattr(config, "GENERATION_API_KEY", "test-key")
    monkeypatch.setattr(config, "GENERATION_MODEL_ID", "test-model")


def _mock_generation_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
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


def _prepare_ticket_at_dept_interrupts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> str:
    monkeypatch.setenv(
        "RFP_CHECKPOINT_DB_PATH",
        str(tmp_path / "rfp_approval_api_checkpoints.db"),
    )
    reset_graph_cache()
    _mock_generation_pipeline(monkeypatch)

    with Session(get_engine()) as session:
        ensure_rfp_schema(session)
        ticket_id = create_ticket_from_pdf(
            session,
            seed_asset_path(SEED_PDF_FILES[1]),
        )
        assert ticket_detail(session, ticket_id).status == STATUS_INTAKE_COMPLETE
        run_generation_for_ticket(session, ticket_id)
        assert ticket_detail(session, ticket_id).status == STATUS_WAITING_FOR_APPROVAL
        run_approval_for_ticket(session, ticket_id)
        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_AWAITING_DEPARTMENT_APPROVAL
        for section in detail.sections:
            assert section.approval_status == APPROVAL_STATUS_AWAITING_HUMAN
    return ticket_id


@pytestmark_db
def test_approval_routes_require_auth(anon_client):
    assert (
        anon_client.post(
            "/rfp/tickets/fake-id/sections/marketing/decision",
            json={"decision": "approve"},
        ).status_code
        == 401
    )
    assert anon_client.post("/rfp/tickets/fake-id/ceo/decision", json={"decision": "approve"}).status_code == 401
    assert anon_client.get("/rfp/tickets/fake-id/final-document").status_code == 401


@pytestmark_db
def test_department_decision_approve_one_dept(client, monkeypatch, tmp_path):
    """200 — approve one department while others remain awaiting_human."""
    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    with Session(get_engine()) as session:
        detail = ticket_detail(session, ticket_id)
        target = detail.sections[0].department_id

    response = client.post(
        f"/rfp/tickets/{ticket_id}/sections/{target}/decision",
        json={"decision": "approve", "comment": "Looks good"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == ticket_id
    assert body["department_id"] == target
    assert body["decision"] == "approve"
    assert body["approval_status"] == APPROVAL_STATUS_APPROVED

    with Session(get_engine()) as session:
        detail = ticket_detail(session, ticket_id)
        assert detail.status != STATUS_COMPLETED
        approved = [s for s in detail.sections if s.approval_status == APPROVAL_STATUS_APPROVED]
        awaiting = [s for s in detail.sections if s.approval_status == APPROVAL_STATUS_AWAITING_HUMAN]
        assert len(approved) == 1
        assert len(awaiting) == len(detail.sections) - 1


@pytestmark_db
def test_department_decision_400_invalid_enum(client, monkeypatch, tmp_path):
    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    response = client.post(
        f"/rfp/tickets/{ticket_id}/sections/marketing/decision",
        json={"decision": "maybe"},
    )
    assert response.status_code == 400


@pytestmark_db
def test_department_decision_404_ticket(client, monkeypatch):
    _stub_generation_env(monkeypatch)
    response = client.post(
        "/rfp/tickets/does-not-exist/sections/marketing/decision",
        json={"decision": "approve"},
    )
    assert response.status_code == 404


@pytestmark_db
def test_department_decision_404_section(client, monkeypatch, tmp_path):
    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    response = client.post(
        f"/rfp/tickets/{ticket_id}/sections/not-a-dept/decision",
        json={"decision": "approve"},
    )
    assert response.status_code == 404


@pytestmark_db
def test_department_decision_409_wrong_phase(client, monkeypatch, tmp_path):
    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    with Session(get_engine()) as session:
        detail = ticket_detail(session, ticket_id)
        target = detail.sections[0].department_id

    first = client.post(
        f"/rfp/tickets/{ticket_id}/sections/{target}/decision",
        json={"decision": "approve"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/rfp/tickets/{ticket_id}/sections/{target}/decision",
        json={"decision": "approve"},
    )
    assert second.status_code == 409


@pytestmark_db
def test_department_decision_409_before_approval_started(client, monkeypatch, tmp_path):
    _stub_generation_env(monkeypatch)
    monkeypatch.setenv("RFP_CHECKPOINT_DB_PATH", str(tmp_path / "rfp_api_no_p3.db"))
    reset_graph_cache()
    _mock_generation_pipeline(monkeypatch)

    with Session(get_engine()) as session:
        ensure_rfp_schema(session)
        ticket_id = create_ticket_from_pdf(
            session,
            seed_asset_path(SEED_PDF_FILES[1]),
        )
        run_generation_for_ticket(session, ticket_id)

    response = client.post(
        f"/rfp/tickets/{ticket_id}/sections/marketing/decision",
        json={"decision": "approve"},
    )
    assert response.status_code == 409


@pytestmark_db
def test_regenerate_409_when_not_rejected(client, monkeypatch, tmp_path):
    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    response = client.post(f"/rfp/tickets/{ticket_id}/sections/marketing/regenerate")
    assert response.status_code == 409


@pytestmark_db
def test_regenerate_after_reject_reopens_interrupt(client, monkeypatch, tmp_path):
    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    reject = client.post(
        f"/rfp/tickets/{ticket_id}/sections/marketing/decision",
        json={"decision": "reject", "comment": "Needs rework"},
    )
    assert reject.status_code == 200

    regen = client.post(f"/rfp/tickets/{ticket_id}/sections/marketing/regenerate")
    assert regen.status_code == 200
    body = regen.json()
    assert body["department_id"] == "marketing"
    assert body["approval_status"] == APPROVAL_STATUS_AWAITING_HUMAN


@pytestmark_db
def test_approve_all_departments_reaches_completed(client, monkeypatch, tmp_path):
    """Seed #2 fast path — no CEO; all dept approvals → completed + final document."""
    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    with Session(get_engine()) as session:
        departments = [s.department_id for s in ticket_detail(session, ticket_id).sections]

    for dept in departments:
        response = client.post(
            f"/rfp/tickets/{ticket_id}/sections/{dept}/decision",
            json={"decision": "approve"},
        )
        assert response.status_code == 200

    with Session(get_engine()) as session:
        detail = ticket_detail(session, ticket_id)
        assert detail.status == STATUS_COMPLETED
        assert detail.has_final_document is True
        assert detail.final_document_length > 0

    doc_response = client.get(f"/rfp/tickets/{ticket_id}/final-document")
    assert doc_response.status_code == 200
    doc = doc_response.json()
    assert doc["ticket_id"] == ticket_id
    assert len(doc["final_document_markdown"]) > 0
    assert doc["generated_at"]


@pytestmark_db
def test_final_document_404_before_complete(client, monkeypatch, tmp_path):
    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    response = client.get(f"/rfp/tickets/{ticket_id}/final-document")
    assert response.status_code == 404


@pytestmark_db
def test_reject_persists_approval_comment(client, monkeypatch, tmp_path):
    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    reject = client.post(
        f"/rfp/tickets/{ticket_id}/sections/marketing/decision",
        json={"decision": "reject", "comment": "Pricing needs revision"},
    )
    assert reject.status_code == 200

    with Session(get_engine()) as session:
        detail = ticket_detail(session, ticket_id)
        marketing = next(s for s in detail.sections if s.department_id == "marketing")
        assert marketing.approval_comment == "Pricing needs revision"


@pytestmark_db
def test_get_trace_returns_persisted_events(client, monkeypatch, tmp_path):
    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    response = client.get(f"/rfp/tickets/{ticket_id}/trace")
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    assert len(events) > 0
    assert events[0]["node"]
    assert "created_at" in events[0]
    payload = events[0]["payload"]
    assert payload.get("agent")
    assert isinstance(payload.get("input"), dict)
    assert isinstance(payload.get("output"), dict)
    assert payload.get("timestamp", "").endswith("Z")


@pytestmark_db
def test_completed_ticket_writes_final_proposal_mirror(client, monkeypatch, tmp_path):
    from data.pipelines.rfp_intake import repo_root

    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    with Session(get_engine()) as session:
        departments = [s.department_id for s in ticket_detail(session, ticket_id).sections]

    for dept in departments:
        response = client.post(
            f"/rfp/tickets/{ticket_id}/sections/{dept}/decision",
            json={"decision": "approve"},
        )
        assert response.status_code == 200

    mirror_path = repo_root() / "data" / "raw" / "intakes" / ticket_id / "final_proposal.md"
    assert mirror_path.is_file()
    assert mirror_path.read_text(encoding="utf-8").strip()


@pytestmark_db
def test_approval_start_recovery_idempotent(client, monkeypatch, tmp_path):
    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    response = client.post(f"/rfp/tickets/{ticket_id}/approval/start")
    assert response.status_code == 200
    assert response.json()["status"] == STATUS_AWAITING_DEPARTMENT_APPROVAL


@pytestmark_db
def test_ceo_decision_409_when_not_required(client, monkeypatch, tmp_path):
    _stub_generation_env(monkeypatch)
    ticket_id = _prepare_ticket_at_dept_interrupts(monkeypatch, tmp_path)

    response = client.post(
        f"/rfp/tickets/{ticket_id}/ceo/decision",
        json={"decision": "approve"},
    )
    assert response.status_code == 409


def test_rfp_approval_routes_registered_on_app():
    from main import app

    paths = set(app.openapi()["paths"])
    assert "/rfp/tickets/{ticket_id}/sections/{department_id}/decision" in paths
    assert "/rfp/tickets/{ticket_id}/sections/{department_id}/regenerate" in paths
    assert "/rfp/tickets/{ticket_id}/ceo/decision" in paths
    assert "/rfp/tickets/{ticket_id}/approval/start" in paths
    assert "/rfp/tickets/{ticket_id}/final-document" in paths
