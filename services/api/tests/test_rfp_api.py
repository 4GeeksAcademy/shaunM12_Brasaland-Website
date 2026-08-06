"""RFP HTTP API tests (context-27 Part 1 — Phase 3 + Phase 5 gate)."""

from __future__ import annotations

import config
import pytest

from rfp.constants import (
    ERROR_PDF_CONVERSION_FAILED,
    SEED_PDF_FILES,
    STATUS_ANALYZING,
    STATUS_DISCARDED,
    STATUS_FAILED,
)
from rfp.intake_service import seed_asset_path

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


def test_rfp_routes_registered_on_app():
    from main import app

    paths = set(app.openapi()["paths"])
    assert "/rfp/tickets" in paths
    assert "/rfp/tickets/{ticket_id}" in paths
