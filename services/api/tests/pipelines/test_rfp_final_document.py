"""Unit tests for P3 final document merge (context-27 P3 Phase 1)."""

from __future__ import annotations

import pytest

from rfp.constants import (
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_REJECTED,
    DEPARTMENT_MARKETING,
    DEPARTMENT_OPERATIONS,
    DEPARTMENT_PROCUREMENT,
)

from data.pipelines.rfp_final_document import (
    DEPARTMENT_SECTION_ORDER,
    SynthesisContext,
    SynthesisGateError,
    SectionSnapshot,
    build_final_document,
    can_synthesize,
)


def _approved_ctx(*, ceo: bool = False, ceo_approved: bool = False) -> SynthesisContext:
    return SynthesisContext(
        metadata={
            "client_name": "Sunset Bay Resorts",
            "service_type": "Resort catering",
            "location": "Cartagena",
            "deadline": "2026-09-30",
        },
        intake_summary="Corporate catering RFP for Sunset Bay.",
        departments_needed=[DEPARTMENT_MARKETING, DEPARTMENT_OPERATIONS],
        sections=[
            SectionSnapshot(
                department_id=DEPARTMENT_MARKETING,
                draft_content="Marketing section with brand pillars and 30-day validity.",
                approval_status=APPROVAL_STATUS_APPROVED,
            ),
            SectionSnapshot(
                department_id=DEPARTMENT_OPERATIONS,
                draft_content="Operations section with 12 business day setup.",
                approval_status=APPROVAL_STATUS_APPROVED,
            ),
        ],
        arbitration_resolutions=[
            {
                "field": "deadline",
                "winning_department_id": DEPARTMENT_OPERATIONS,
                "resolved_value": "2026-09-15",
                "rule_id": "ARBITRATION_STRICTEST_OPERATIONAL",
            }
        ],
        requires_ceo_approval=ceo,
        ceo_approved=ceo_approved,
    )


def test_build_final_document_deterministic_structure():
    doc = build_final_document(_approved_ctx())
    assert "# Brasaland Proposal — Sunset Bay Resorts" in doc
    assert "## Executive summary" in doc
    assert "Corporate catering RFP" in doc
    assert "### Marketing and Digital Experience" in doc
    assert "Marketing section with brand pillars" in doc
    assert "### Restaurant Operations" in doc
    assert "12 business day setup" in doc
    assert "## Arbitration resolutions" in doc
    assert "COMPLIANCE_VALIDITY_30_DAYS" in doc


def test_department_section_order_fixed():
    ctx = _approved_ctx()
    ctx.departments_needed = [
        DEPARTMENT_PROCUREMENT,
        DEPARTMENT_MARKETING,
        DEPARTMENT_OPERATIONS,
    ]
    ctx.sections.append(
        SectionSnapshot(
            department_id=DEPARTMENT_PROCUREMENT,
            draft_content="Procurement pricing.",
            approval_status=APPROVAL_STATUS_APPROVED,
        )
    )
    doc = build_final_document(ctx)
    marketing_idx = doc.index("### Marketing and Digital Experience")
    operations_idx = doc.index("### Restaurant Operations")
    procurement_idx = doc.index("### Procurement and Suppliers")
    assert marketing_idx < operations_idx < procurement_idx
    assert list(DEPARTMENT_SECTION_ORDER)[0] == DEPARTMENT_MARKETING


def test_can_synthesize_false_when_section_not_approved():
    ctx = _approved_ctx()
    ctx.sections[0].approval_status = None
    assert can_synthesize(ctx) is False


def test_can_synthesize_false_when_section_rejected():
    ctx = _approved_ctx()
    ctx.sections[1].approval_status = APPROVAL_STATUS_REJECTED
    assert can_synthesize(ctx) is False


def test_can_synthesize_false_when_arbitration_exhausted():
    ctx = _approved_ctx()
    ctx.arbitration_exhausted = True
    assert can_synthesize(ctx) is False


def test_can_synthesize_false_when_ceo_required_not_approved():
    ctx = _approved_ctx(ceo=True, ceo_approved=False)
    assert can_synthesize(ctx) is False


def test_build_raises_when_ceo_gate_not_cleared():
    ctx = _approved_ctx(ceo=True, ceo_approved=False)
    with pytest.raises(SynthesisGateError, match="CEO approval"):
        build_final_document(ctx)


def test_build_succeeds_when_ceo_approved():
    doc = build_final_document(_approved_ctx(ceo=True, ceo_approved=True))
    assert "Sunset Bay Resorts" in doc
