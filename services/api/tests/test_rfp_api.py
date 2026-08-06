"""RFP HTTP API tests (context-27 Part 1 — Phase 3 + Phase 5 gate)."""

from __future__ import annotations

import config
import pytest

from rfp.constants import (
    DEPARTMENT_MARKETING,
    DRAFT_STATUS_PENDING,
    ERROR_PDF_CONVERSION_FAILED,
    SEED_PDF_FILES,
    STATUS_ANALYZING,
    STATUS_DISCARDED,
    STATUS_DRAFTING,
    STATUS_FAILED,
    STATUS_WAITING_FOR_APPROVAL,
)
from rfp.intake_service import seed_asset_path
from rfp.repository import create_ticket_analyzing, upsert_department_section
from database import get_engine
from rfp.models import ensure_rfp_schema
from sqlmodel import Session

pytestmark_db = pytest.mark.skipif(
    not config.DATABASE_URL,
    reason="DATABASE_URL not set — RFP API integration tests require PostgreSQL",
)


def _stub_generation_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GENERATION_BASE_URL", "http://gen.test/v1")
    monkeypatch.setenv("GENERATION_API_KEY", "test-key")
    monkeypatch.setenv("GENERATION_MODEL_ID", "test-model")
    monkeypatch.setattr(config, "GENERATION_BASE_URL", "http://gen.test/v1")
    monkeypatch.setattr(config, "GENERATION_API_KEY", "test-key")
    monkeypatch.setattr(config, "GENERATION_MODEL_ID", "test-model")


def test_rfp_routes_require_auth(anon_client):
    assert anon_client.get("/rfp/tickets").status_code == 401
    assert anon_client.get("/rfp/tickets/fake-id").status_code == 401
    assert anon_client.post("/rfp/tickets").status_code == 401


def test_post_rfp_ticket_requires_database(client, monkeypatch):
    monkeypatch.setattr(config, "DATABASE_URL", None)
    monkeypatch.setenv("GENERATION_BASE_URL", "http://gen.test/v1")
    monkeypatch.setenv("GENERATION_API_KEY", "test-key")
    monkeypatch.setenv("GENERATION_MODEL_ID", "test-model")
    monkeypatch.setattr(config, "GENERATION_BASE_URL", "http://gen.test/v1")
    monkeypatch.setattr(config, "GENERATION_API_KEY", "test-key")
    monkeypatch.setattr(config, "GENERATION_MODEL_ID", "test-model")

    response = client.post(
        "/rfp/tickets",
        files={"file": ("sample.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert response.status_code == 503


def test_post_rfp_ticket_requires_generation(client, monkeypatch):
    if not config.DATABASE_URL:
        pytest.skip("DATABASE_URL required for this test")
    monkeypatch.setattr(config, "GENERATION_BASE_URL", None)
    monkeypatch.setattr(config, "GENERATION_API_KEY", None)
    monkeypatch.setattr(config, "GENERATION_MODEL_ID", None)

    response = client.post(
        "/rfp/tickets",
        files={"file": ("sample.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert response.status_code == 503


def test_post_rfp_ticket_rejects_non_pdf(client, monkeypatch):
    if not config.DATABASE_URL:
        pytest.skip("DATABASE_URL required for this test")
    _stub_generation_env(monkeypatch)

    response = client.post(
        "/rfp/tickets",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_post_rfp_ticket_rejects_oversized_pdf(client, monkeypatch):
    if not config.DATABASE_URL:
        pytest.skip("DATABASE_URL required for this test")
    _stub_generation_env(monkeypatch)

    response = client.post(
        "/rfp/tickets",
        files={
            "file": (
                "large.pdf",
                b"%PDF" + (b"0" * (10 * 1024 * 1024)),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 400


@pytestmark_db
def test_post_and_get_rfp_ticket(client, monkeypatch):
    _stub_generation_env(monkeypatch)
    monkeypatch.setattr(
        "rfp.routes.run_intake_background_task",
        lambda ticket_id: None,
    )

    pdf_bytes = seed_asset_path(SEED_PDF_FILES[2]).read_bytes()
    create_response = client.post(
        "/rfp/tickets",
        files={"file": (SEED_PDF_FILES[2], pdf_bytes, "application/pdf")},
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["status"] == STATUS_ANALYZING
    ticket_id = body["ticket_id"]

    list_response = client.get("/rfp/tickets")
    assert list_response.status_code == 200
    summaries = list_response.json()
    assert any(row["ticket_id"] == ticket_id for row in summaries)

    detail_response = client.get(f"/rfp/tickets/{ticket_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["ticket_id"] == ticket_id
    assert detail["status"] == STATUS_ANALYZING
    assert detail["has_markdown"] is False


@pytestmark_db
def test_get_rfp_ticket_not_found(client):
    response = client.get("/rfp/tickets/does-not-exist")
    assert response.status_code == 404


@pytestmark_db
def test_post_upload_reaches_discarded_terminal(client, monkeypatch, tmp_path):
    """Async upload + background intake — TestClient runs BackgroundTasks inline."""
    monkeypatch.setenv("RFP_CHECKPOINT_DB_PATH", str(tmp_path / "rfp_checkpoints.db"))
    from rfp.graph import reset_graph_cache

    reset_graph_cache()
    _stub_generation_env(monkeypatch)

    pdf_bytes = seed_asset_path(SEED_PDF_FILES[2]).read_bytes()
    create_response = client.post(
        "/rfp/tickets",
        files={"file": (SEED_PDF_FILES[2], pdf_bytes, "application/pdf")},
    )
    assert create_response.status_code == 201
    ticket_id = create_response.json()["ticket_id"]

    detail_response = client.get(f"/rfp/tickets/{ticket_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == STATUS_DISCARDED
    assert detail["status_label"] == "Discarded"
    assert detail["discard_reason"]
    assert detail["sections"] == []


@pytestmark_db
def test_post_corrupt_pdf_failed_via_api(client, monkeypatch, tmp_path):
    monkeypatch.setenv("RFP_CHECKPOINT_DB_PATH", str(tmp_path / "rfp_api_checkpoints.db"))
    from rfp.graph import reset_graph_cache

    reset_graph_cache()
    _stub_generation_env(monkeypatch)

    def _raise_conversion(_path):
        raise ValueError("PDF conversion produced empty text")

    monkeypatch.setattr(
        "data.pipelines.rfp_intake.convert_pdf_to_markdown",
        _raise_conversion,
    )

    create_response = client.post(
        "/rfp/tickets",
        files={
            "file": (
                "corrupt.pdf",
                b"%PDF-1.4\nnot a valid pdf document",
                "application/pdf",
            )
        },
    )
    assert create_response.status_code == 201
    ticket_id = create_response.json()["ticket_id"]

    detail_response = client.get(f"/rfp/tickets/{ticket_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == STATUS_FAILED
    assert detail["error_code"] == ERROR_PDF_CONVERSION_FAILED


@pytestmark_db
def test_list_rfp_tickets_rejects_invalid_status(client):
    response = client.get("/rfp/tickets?status=not-a-real-status")
    assert response.status_code == 400


@pytestmark_db
def test_get_rfp_ticket_returns_section_draft_status(client):
    """Part 2 Phase 0 — GET detail exposes draft_status on each section."""
    with Session(get_engine()) as session:
        ensure_rfp_schema(session)
        ticket = create_ticket_analyzing(session)
        ticket_id = ticket.ticket_id
        upsert_department_section(
            session,
            ticket_id=ticket_id,
            department_id=DEPARTMENT_MARKETING,
            key_aspects=["Co-marketing"],
        )

    response = client.get(f"/rfp/tickets/{ticket_id}")
    assert response.status_code == 200
    detail = response.json()
    assert len(detail["sections"]) == 1
    section = detail["sections"][0]
    assert section["department_id"] == DEPARTMENT_MARKETING
    assert section["draft_status"] == DRAFT_STATUS_PENDING
    assert section["draft_status_label"] == "Pending"


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


@pytestmark_db
def test_post_draft_requires_auth(anon_client):
    response = anon_client.post("/rfp/tickets/fake-id/draft")
    assert response.status_code == 401


@pytestmark_db
def test_post_draft_from_intake_complete_reaches_waiting_for_approval(
    client,
    monkeypatch,
    tmp_path,
):
    """Phase 3 gate — POST draft + poll GET until P2 terminal."""
    monkeypatch.setenv("RFP_CHECKPOINT_DB_PATH", str(tmp_path / "rfp_api_draft.db"))
    from rfp.graph import reset_graph_cache

    reset_graph_cache()
    _stub_generation_env(monkeypatch)
    _mock_generation_pipeline(monkeypatch)

    with Session(get_engine()) as session:
        from rfp.intake_service import create_ticket_from_pdf, seed_asset_path

        ticket_id = create_ticket_from_pdf(
            session,
            seed_asset_path(SEED_PDF_FILES[1]),
        )

    draft_response = client.post(f"/rfp/tickets/{ticket_id}/draft")
    assert draft_response.status_code == 201
    body = draft_response.json()
    assert body["ticket_id"] == ticket_id
    assert body["status"] == STATUS_DRAFTING
    assert body["status_label"] == "Drafting"

    detail_response = client.get(f"/rfp/tickets/{ticket_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == STATUS_WAITING_FOR_APPROVAL
    assert detail["status_label"] == "Waiting for approval"
    assert len(detail["sections"]) == 3
    for section in detail["sections"]:
        assert section["draft_content"]
        assert section["evaluation_results"]
        assert section["draft_status"] in ("passed", "needs_human_review")


@pytestmark_db
def test_post_draft_returns_409_when_not_intake_complete(client, monkeypatch):
    _stub_generation_env(monkeypatch)
    monkeypatch.setattr(
        "rfp.routes.run_intake_background_task",
        lambda ticket_id: None,
    )

    pdf_bytes = seed_asset_path(SEED_PDF_FILES[2]).read_bytes()
    create_response = client.post(
        "/rfp/tickets",
        files={"file": (SEED_PDF_FILES[2], pdf_bytes, "application/pdf")},
    )
    ticket_id = create_response.json()["ticket_id"]

    draft_response = client.post(f"/rfp/tickets/{ticket_id}/draft")
    assert draft_response.status_code == 409

    second_response = client.post(f"/rfp/tickets/{ticket_id}/draft")
    assert second_response.status_code == 409


@pytestmark_db
def test_post_draft_returns_409_after_success(client, monkeypatch, tmp_path):
    monkeypatch.setenv("RFP_CHECKPOINT_DB_PATH", str(tmp_path / "rfp_api_draft_409.db"))
    from rfp.graph import reset_graph_cache

    reset_graph_cache()
    _stub_generation_env(monkeypatch)
    _mock_generation_pipeline(monkeypatch)

    with Session(get_engine()) as session:
        from rfp.intake_service import create_ticket_from_pdf, seed_asset_path

        ticket_id = create_ticket_from_pdf(
            session,
            seed_asset_path(SEED_PDF_FILES[1]),
        )

    first = client.post(f"/rfp/tickets/{ticket_id}/draft")
    assert first.status_code == 201

    second = client.post(f"/rfp/tickets/{ticket_id}/draft")
    assert second.status_code == 409
    payload = second.json()
    assert payload["detail"]["status"] == STATUS_WAITING_FOR_APPROVAL


@pytestmark_db
def test_post_draft_not_found(client, monkeypatch):
    _stub_generation_env(monkeypatch)
    response = client.post("/rfp/tickets/does-not-exist/draft")
    assert response.status_code == 404


@pytestmark_db
def test_delete_rfp_ticket_removes_row(client, monkeypatch):
    _stub_generation_env(monkeypatch)
    with Session(get_engine()) as session:
        ensure_rfp_schema(session)
        ticket = create_ticket_analyzing(session)
        ticket_id = ticket.ticket_id

    response = client.delete(f"/rfp/tickets/{ticket_id}")
    assert response.status_code == 204

    with Session(get_engine()) as session:
        from rfp.repository import get_ticket

        assert get_ticket(session, ticket_id) is None


@pytestmark_db
def test_delete_rfp_ticket_not_found(client, monkeypatch):
    _stub_generation_env(monkeypatch)
    response = client.delete("/rfp/tickets/does-not-exist")
    assert response.status_code == 404


@pytestmark_db
def test_delete_rfp_ticket_requires_auth(anon_client):
    response = anon_client.delete("/rfp/tickets/fake-id")
    assert response.status_code == 401


def test_rfp_routes_registered_on_app():
    from main import app

    paths = set(app.openapi()["paths"])
    assert "/rfp/tickets" in paths
    assert "/rfp/tickets/{ticket_id}" in paths
    assert "/rfp/tickets/{ticket_id}/draft" in paths
