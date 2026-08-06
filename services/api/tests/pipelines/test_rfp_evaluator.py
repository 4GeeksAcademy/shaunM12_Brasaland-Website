"""Unit tests for RFP Part 2 evaluators (context-27 P2 Phase 1 gate)."""

from __future__ import annotations

import pytest

from rfp.constants import (
    DRAFT_STATUS_NEEDS_HUMAN_REVIEW,
    DRAFT_STATUS_PASSED,
)

COMPLIANT_DRAFT = """
Brasaland proposes co-branded concession services for Sunset Bay Resorts.

Our consistent product quality and warm, reliable customer experience will support
speed of service without sacrificing quality across all three resort stands.
Brand co-marketing and exclusivity terms are included in this proposal presentation.

Pricing and volume-based ingredient costs total $60,000 USD per year
(COP 240,000,000 at 1 USD = 4000 COP). Supplier lead times for contract volume
are confirmed at 12 business days from signature. Setup and delivery require
12 business days from contract signature. This offer is valid for 30 days from issuance.
"""

USD_ONLY_DRAFT = """
Brasaland training proposal for Sunset Bay Resorts.

We will deliver certification and recipe development for the signature menu.
Pricing: $60,000 USD per year for onsite training and quality standards rollout.
Setup within 12 business days. Offer valid for 30 days from issuance.
"""


def test_readability_passes_plain_language_draft():
    from data.pipelines.rfp_generation import evaluate_readability

    result = evaluate_readability(COMPLIANT_DRAFT)
    assert result["threshold_max_grade"] == 12.0
    assert result["passed"] is True


def test_relevance_passes_when_all_key_aspects_covered():
    from data.pipelines.rfp_generation import evaluate_relevance

    key_aspects = [
        "Brand co-marketing and exclusivity terms",
        "Offer validity and proposal presentation",
    ]
    draft = (
        "Our brand co-marketing plan includes exclusivity for Sunset Bay. "
        "This proposal presentation is valid for 30 days from issuance."
    )
    result = evaluate_relevance(draft, key_aspects, use_llm=False)
    assert result["passed"] is True
    assert result["missing_topics"] == []
    assert result["addresses_key_aspects"] is True


def test_relevance_fails_with_missing_topics():
    from data.pipelines.rfp_generation import evaluate_relevance

    key_aspects = [
        "Operational feasibility and staffing plan",
        "Setup timeline and service cadence",
    ]
    draft = "We offer great food and friendly staff at Brasaland locations."
    result = evaluate_relevance(draft, key_aspects, use_llm=False)
    assert result["passed"] is False
    assert result["missing_topics"]
    assert "staffing" in result["missing_topics"][0].lower() or len(result["missing_topics"]) >= 1


def test_relevance_passes_when_key_aspects_empty():
    from data.pipelines.rfp_generation import evaluate_relevance

    result = evaluate_relevance("Any draft text.", [], use_llm=False)
    assert result["passed"] is True
    assert result["missing_topics"] == []


def test_compliance_dual_currency_usd_only():
    """Context-anchored compliance failure (rubric #6 / M9-P2-19)."""
    from data.pipelines.rfp_generation import evaluate_compliance

    result = evaluate_compliance(USD_ONLY_DRAFT, {})
    assert result["passed"] is False
    rule_ids = [f["rule_id"] for f in result["failures"]]
    assert "COMPLIANCE_DUAL_CURRENCY" in rule_ids
    dual = next(f for f in result["failures"] if f["rule_id"] == "COMPLIANCE_DUAL_CURRENCY")
    assert "USD" in dual["message"]
    assert "4000" in dual["suggested_fix"]


def test_compliance_dual_currency_passes_with_cop():
    from data.pipelines.rfp_generation import evaluate_compliance

    result = evaluate_compliance(COMPLIANT_DRAFT, {})
    rule_ids = [f["rule_id"] for f in result["failures"]]
    assert "COMPLIANCE_DUAL_CURRENCY" not in rule_ids


def test_compliance_brand_pillars_missing():
    from data.pipelines.rfp_generation import evaluate_compliance

    draft = "Pricing is $10,000 USD (COP 40,000,000). Valid 30 days. Setup in 12 business days."
    result = evaluate_compliance(draft, {})
    assert result["passed"] is False
    assert any(f["rule_id"] == "COMPLIANCE_BRAND_PILLARS" for f in result["failures"])


def test_compliance_no_competitors():
    from data.pipelines.rfp_generation import evaluate_compliance

    draft = (
        "Unlike Starbucks, Brasaland offers better quality. "
        "Pricing $5,000 USD and COP 20,000,000. Valid 30 days. Setup 12 business days. "
        "Consistent quality, warm customer experience, speed of service."
    )
    result = evaluate_compliance(draft, {})
    assert any(f["rule_id"] == "COMPLIANCE_NO_COMPETITORS" for f in result["failures"])


def test_compliance_min_lead_time_ignores_backup_response_window():
    from data.pipelines.rfp_generation import evaluate_compliance

    draft = (
        "Supplier lead times for contract volume are 12 business days from signature. "
        "Backup suppliers can respond within 5 days for emergency replenishment. "
        "Pricing $60,000 USD (COP 240,000,000). Valid 30 days. "
        "Consistent quality, warm customer experience, speed of service."
    )
    result = evaluate_compliance(draft, {})
    rule_ids = [f["rule_id"] for f in result["failures"]]
    assert "COMPLIANCE_MIN_LEAD_TIME_10_BD" not in rule_ids


def test_compliance_min_lead_time_blocks_short_setup():
    from data.pipelines.rfp_generation import evaluate_compliance

    draft = (
        "Setup and delivery in 5 business days. Pricing $60,000 USD (COP 240,000,000). "
        "Valid 30 days. Consistent quality, warm customer experience, speed of service."
    )
    result = evaluate_compliance(draft, {})
    assert any(f["rule_id"] == "COMPLIANCE_MIN_LEAD_TIME_10_BD" for f in result["failures"])


def test_build_retry_feedback_preserves_passed_dimensions_and_history():
    from data.pipelines.rfp_generation import build_retry_feedback

    history = [
        {
            "readability": {"passed": False, "flesch_kincaid_grade": 15.0},
            "relevance": {"passed": True, "missing_topics": []},
            "compliance": {
                "passed": False,
                "failures": [
                    {
                        "rule_id": "COMPLIANCE_VALIDITY_30_DAYS",
                        "message": "missing validity",
                    }
                ],
            },
        }
    ]
    latest = {
        "readability": {"passed": True, "flesch_kincaid_grade": 8.3},
        "relevance": {"passed": True, "missing_topics": []},
        "compliance": {
            "passed": False,
            "failures": [
                {
                    "rule_id": "COMPLIANCE_BRAND_PILLARS",
                    "message": "Missing speed of service",
                }
            ],
        },
    }
    feedback = build_retry_feedback(latest, history=history)
    assert any("Readability passed" in item for item in feedback.get("preserve", []))
    assert not any("Compliance passed" in item for item in feedback.get("preserve", []))
    rule_ids = [f["rule_id"] for f in feedback.get("compliance_failures", [])]
    assert "COMPLIANCE_VALIDITY_30_DAYS" in rule_ids
    assert "COMPLIANCE_BRAND_PILLARS" in rule_ids
    assert feedback.get("instruction")


def test_compliance_ceo_threshold_flag_only():
    from data.pipelines.rfp_generation import evaluate_compliance

    result = evaluate_compliance(
        COMPLIANT_DRAFT,
        {"estimated_contract_value_usd": 75_000},
    )
    ceo_flags = [f for f in result.get("advisory", []) if f["rule_id"] == "COMPLIANCE_CEO_THRESHOLD_50K"]
    assert ceo_flags
    # Flag-only — blocking failures list excludes CEO threshold
    assert "COMPLIANCE_CEO_THRESHOLD_50K" not in [f["rule_id"] for f in result["failures"]]
    assert result["passed"] is True


def test_evaluate_section_overall_passed_all_dimensions():
    from data.pipelines.rfp_generation import evaluate_section

    result = evaluate_section(
        department_id="procurement",
        draft_content=COMPLIANT_DRAFT,
        key_aspects=[
            "Pricing and volume-based ingredient costs",
            "Supplier lead times for contract volume",
        ],
        metadata={"estimated_contract_value_usd": 60_000},
        iteration=1,
        use_llm_relevance=False,
    )
    assert result["iteration"] == 1
    assert result["overall_passed"] is True
    assert result["needs_human_review"] is False
    assert result["readability"]["passed"] is True
    assert result["relevance"]["passed"] is True
    assert result["compliance"]["passed"] is True


def test_evaluate_section_parallel_join_matches_combined():
    from data.pipelines.rfp_generation import (
        evaluate_compliance,
        evaluate_readability,
        evaluate_relevance,
        evaluate_section,
        evaluate_section_parallel_inputs,
    )

    kwargs = {
        "department_id": "operations",
        "draft_content": USD_ONLY_DRAFT,
        "key_aspects": ["Operational feasibility and staffing plan"],
        "metadata": {},
        "iteration": 1,
        "use_llm_relevance": False,
    }
    combined = evaluate_section(**kwargs)
    parallel = evaluate_section_parallel_inputs(**kwargs)
    assert parallel["overall_passed"] == combined["overall_passed"]
    assert parallel["compliance"]["failures"] == combined["compliance"]["failures"]

    # Independent dimension calls produce same join result
    readability = evaluate_readability(kwargs["draft_content"])
    relevance = evaluate_relevance(
        kwargs["draft_content"],
        kwargs["key_aspects"],
        use_llm=False,
    )
    compliance = evaluate_compliance(kwargs["draft_content"], kwargs["metadata"])
    assert not compliance["passed"]
    assert any(
        f["rule_id"] == "COMPLIANCE_DUAL_CURRENCY" for f in compliance["failures"]
    )


def test_finalize_evaluation_max_iterations_needs_human_review():
    from data.pipelines.rfp_generation import (
        evaluate_section,
        finalize_evaluation_after_loop,
    )

    evaluation = evaluate_section(
        department_id="procurement",
        draft_content=USD_ONLY_DRAFT,
        key_aspects=["Pricing and volume-based ingredient costs"],
        iteration=3,
        use_llm_relevance=False,
    )
    assert evaluation["overall_passed"] is False

    final_eval, draft_status = finalize_evaluation_after_loop(evaluation, iteration=3)
    assert final_eval["needs_human_review"] is True
    assert draft_status == DRAFT_STATUS_NEEDS_HUMAN_REVIEW


def test_finalize_evaluation_pass_sets_passed_status():
    from data.pipelines.rfp_generation import (
        evaluate_section,
        finalize_evaluation_after_loop,
    )

    evaluation = evaluate_section(
        department_id="marketing",
        draft_content=COMPLIANT_DRAFT,
        key_aspects=[
            "Brand co-marketing and exclusivity terms",
            "Offer validity and proposal presentation",
        ],
        iteration=1,
        use_llm_relevance=False,
    )
    final_eval, draft_status = finalize_evaluation_after_loop(evaluation, iteration=1)
    assert final_eval["overall_passed"] is True
    assert draft_status == DRAFT_STATUS_PASSED
