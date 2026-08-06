"""Unit tests for RFP classifier and worker agents (context-27 evaluation criteria)."""

from __future__ import annotations

import pytest

from rfp.constants import (
    DEPARTMENT_OPERATIONS,
    DEPARTMENT_TRAINING,
    department_owner,
    status_label,
)

FRANCHISE_MARKDOWN = """
Franchise Inquiry
Hello, I wanted to ask whether you offer franchises in Cali.
I do not have a full plan put together yet.
Best regards, Andres Salazar
"""

SUNSET_BAY_MARKDOWN = """
Sunset Bay Resorts - RFP
REQUEST FOR PROPOSAL (RFP)
Proposal Due Date: September 2, 2026
Scope of Work: co-branded signature menu, exclusivity
Estimated annual contract value: $60,000-$75,000 USD
Staffing plan covering peak season operations
"""

ANDES_TECH_MARKDOWN = """
Andes Tech Solutions - Catering Inquiry
We would like weekly catering for around 220 people in Medellín.
Would it be possible before August 18?
Daniela Rojas, People & Workplace Lead
"""


def test_classify_document_rejects_franchise_inquiry():
    from data.pipelines.rfp_intake import classify_document

    result = classify_document(FRANCHISE_MARKDOWN)
    assert result.status == "discarded"
    assert result.discard_reason
    assert result.departments_needed == []


def test_classify_document_accepts_sunset_bay_rfp():
    from data.pipelines.rfp_intake import classify_document

    result = classify_document(SUNSET_BAY_MARKDOWN)
    assert result.status == "intake_complete"
    assert result.metadata.get("client_name") == "Sunset Bay Resorts, LLC"
    assert result.requires_ceo_approval is True
    assert DEPARTMENT_TRAINING in result.departments_needed
    assert len(result.departments_needed) == 4


def test_classify_document_routes_andes_tech_without_training():
    from data.pipelines.rfp_intake import classify_document

    result = classify_document(ANDES_TECH_MARKDOWN)
    assert result.status == "intake_complete"
    assert result.requires_ceo_approval is False
    assert len(result.departments_needed) == 3
    assert DEPARTMENT_TRAINING not in result.departments_needed


def test_classify_rejection_does_not_raise():
    """Discarding a non-RFP must not stop the classifier (returns result, no throw)."""
    from data.pipelines.rfp_intake import classify_document

    results = [classify_document(FRANCHISE_MARKDOWN) for _ in range(3)]
    assert all(r.status == "discarded" for r in results)


def test_generate_key_aspects_worker_operations_template(monkeypatch: pytest.MonkeyPatch):
    from data.pipelines import rfp_intake as pipeline

    monkeypatch.setattr(pipeline, "_generation_available", lambda: False)

    aspects = pipeline.generate_key_aspects(
        DEPARTMENT_OPERATIONS,
        {"client_name": "Sunset Bay Resorts, LLC", "deadline": "2026-09-02"},
        "Staffing plan covering peak season and off-season operations.",
    )
    assert len(aspects) >= 2
    assert any("staff" in aspect.lower() for aspect in aspects)


def test_generate_key_aspects_worker_marketing_template(monkeypatch: pytest.MonkeyPatch):
    from data.pipelines import rfp_intake as pipeline

    monkeypatch.setattr(pipeline, "_generation_available", lambda: False)

    aspects = pipeline.generate_key_aspects(
        "marketing",
        {"client_name": "Andes Tech Solutions"},
        "Brand co-marketing and exclusivity terms for the proposal.",
    )
    assert len(aspects) >= 2
    assert any("brand" in aspect.lower() for aspect in aspects)


def test_department_owner_mapping_matches_context():
    assert department_owner("marketing") == "Camila Ospina"
    assert department_owner("operations") == "Felipe Guerrero"
    assert department_owner("procurement") == "Lucia Fernandez"
    assert department_owner("training") == "Jake Morrison"


def test_status_labels_cover_p1_and_approval_flow():
    assert status_label("analyzing") == "Analyzing"
    assert status_label("intake_complete") == "Intake complete"
    assert status_label("discarded") == "Discarded"
    assert status_label("waiting_for_approval") == "Waiting for approval"
    assert status_label("completed") == "Done"


def test_compute_readability_scores_on_converted_seed_markdown():
    from data.pipelines.rfp_intake import compute_readability_scores, convert_pdf_to_markdown
    from rfp.constants import SEED_PDF_FILES
    from rfp.intake_service import seed_asset_path

    markdown = convert_pdf_to_markdown(seed_asset_path(SEED_PDF_FILES[0]))
    scores = compute_readability_scores(markdown)
    assert isinstance(scores, dict)
    assert scores.get("flesch_reading_ease") is not None
