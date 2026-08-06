"""Unit tests for RFP Part 2 generation helpers and loop utilities (context-27 P2 Phase 1)."""

from __future__ import annotations

import pytest

from rfp.constants import (
    DEPARTMENT_MARKETING,
    DEPARTMENT_OPERATIONS,
    DEPARTMENT_PROCUREMENT,
    DEPARTMENT_TRAINING,
    DRAFT_STATUS_EVALUATING,
    DRAFT_STATUS_NEEDS_HUMAN_REVIEW,
    DRAFT_STATUS_PASSED,
)

COMPLIANT_DRAFT = """
Brasaland proposes co-branded concession services for Sunset Bay Resorts.
Our consistent product quality and warm customer experience support
speed of service without sacrificing quality at every location.
Brand co-marketing and exclusivity terms are central to this proposal presentation.
Pricing is $60,000 USD (COP 240,000,000). Setup in 12 business days. Valid 30 days.
"""


def test_generators_registry_covers_all_departments():
    from data.pipelines.rfp_generation import GENERATORS

    for dept in (
        DEPARTMENT_MARKETING,
        DEPARTMENT_OPERATIONS,
        DEPARTMENT_PROCUREMENT,
        DEPARTMENT_TRAINING,
    ):
        assert dept in GENERATORS
        assert callable(GENERATORS[dept])


def test_generate_draft_raises_when_llm_unavailable(monkeypatch: pytest.MonkeyPatch):
    """M9-P2-M7 — no template fallback when LLM is unavailable."""
    from data.pipelines import rfp_generation as gen
    from data.pipelines.rfp_generation import GenerationUnavailableError, GeneratorContext

    monkeypatch.setattr(gen, "_generation_available", lambda: False)

    ctx = GeneratorContext(
        department_id=DEPARTMENT_OPERATIONS,
        metadata={"client_name": "Sunset Bay"},
        key_aspects=["Staffing plan"],
    )
    with pytest.raises(GenerationUnavailableError):
        gen.generate_draft(ctx)


def test_generate_draft_with_mock_llm(monkeypatch: pytest.MonkeyPatch):
    from data.pipelines import rfp_generation as gen
    from data.pipelines.rfp_generation import GeneratorContext

    monkeypatch.setattr(gen, "_generation_available", lambda: True)
    monkeypatch.setattr(
        gen,
        "_chat_text",
        lambda system, user: "Mock operations draft with staffing plan.",
    )

    ctx = GeneratorContext(
        department_id=DEPARTMENT_OPERATIONS,
        metadata={"client_name": "Sunset Bay"},
        key_aspects=["Operational feasibility and staffing plan"],
        excerpt="Peak season staffing requirements.",
    )
    draft = gen.generate_draft(ctx)
    assert "staffing" in draft.lower()


def test_build_retry_feedback_includes_missing_topics_and_compliance():
    from data.pipelines.rfp_generation import build_retry_feedback

    evaluation = {
        "readability": {"passed": True},
        "relevance": {
            "passed": False,
            "missing_topics": ["peak season staffing"],
        },
        "compliance": {
            "passed": False,
            "failures": [
                {
                    "rule_id": "COMPLIANCE_DUAL_CURRENCY",
                    "message": "USD only",
                    "suggested_fix": "Add COP",
                }
            ],
        },
    }
    feedback = build_retry_feedback(evaluation)
    assert feedback["missing_topics"] == ["peak season staffing"]
    assert feedback["compliance_failures"][0]["rule_id"] == "COMPLIANCE_DUAL_CURRENCY"


def test_should_retry_evaluation_respects_iteration_cap():
    from data.pipelines.rfp_generation import should_retry_evaluation

    failed = {"overall_passed": False}
    assert should_retry_evaluation(failed, iteration=1) is True
    assert should_retry_evaluation(failed, iteration=2) is True
    assert should_retry_evaluation(failed, iteration=3) is False

    passed = {"overall_passed": True}
    assert should_retry_evaluation(passed, iteration=1) is False


def test_append_evaluation_history_preserves_prior_iterations():
    from data.pipelines.rfp_generation import EvaluationEnvelope, append_evaluation_history

    first = {
        "iteration": 1,
        "department_id": "marketing",
        "overall_passed": False,
    }
    second = {
        "iteration": 2,
        "department_id": "marketing",
        "overall_passed": False,
    }
    envelope = append_evaluation_history(
        EvaluationEnvelope(latest=first, history=[]),
        second,
    )
    assert envelope.latest == second
    assert len(envelope.history) == 1
    assert envelope.history[0]["iteration"] == 1
    assert envelope.to_dict()["history"][0]["iteration"] == 1


def test_resolve_draft_status_after_evaluation():
    from data.pipelines.rfp_generation import resolve_draft_status_after_evaluation

    assert (
        resolve_draft_status_after_evaluation({"overall_passed": True}, iteration=1)
        == DRAFT_STATUS_PASSED
    )
    assert (
        resolve_draft_status_after_evaluation({"overall_passed": False}, iteration=1)
        == DRAFT_STATUS_EVALUATING
    )
    assert (
        resolve_draft_status_after_evaluation(
            {"overall_passed": False, "needs_human_review": True},
            iteration=3,
        )
        == DRAFT_STATUS_NEEDS_HUMAN_REVIEW
    )


def test_run_single_evaluation_loop_iteration_with_mock_generator(
    monkeypatch: pytest.MonkeyPatch,
):
    """Simulate one generate → evaluate → pass cycle (Phase 2 graph preview)."""
    from data.pipelines import rfp_generation as gen
    from data.pipelines.rfp_generation import (
        GeneratorContext,
        append_evaluation_history,
        build_retry_feedback,
        evaluate_section,
        finalize_evaluation_after_loop,
        should_retry_evaluation,
    )

    monkeypatch.setattr(gen, "_generation_available", lambda: True)
    monkeypatch.setattr(
        gen,
        "_chat_text",
        lambda system, user: COMPLIANT_DRAFT,
    )

    ctx = GeneratorContext(
        department_id=DEPARTMENT_MARKETING,
        metadata={"client_name": "Sunset Bay"},
        key_aspects=[
            "Brand co-marketing and exclusivity terms",
            "Offer validity and proposal presentation",
        ],
    )
    draft = gen.generate_draft(ctx)
    evaluation = evaluate_section(
        department_id=ctx.department_id,
        draft_content=draft,
        key_aspects=ctx.key_aspects,
        iteration=1,
        use_llm_relevance=False,
    )
    final_eval, draft_status = finalize_evaluation_after_loop(evaluation, iteration=1)
    assert final_eval["overall_passed"] is True
    assert draft_status == DRAFT_STATUS_PASSED
    assert should_retry_evaluation(final_eval, iteration=1) is False
    feedback = build_retry_feedback(final_eval)
    assert "missing_topics" not in feedback
    assert "compliance_failures" not in feedback
    assert "readability" not in feedback

    envelope = append_evaluation_history(None, final_eval)
    assert envelope.latest["overall_passed"] is True


def test_relevance_retry_increments_iteration_in_history(monkeypatch: pytest.MonkeyPatch):
    """Generic evaluation failure — relevance miss then retry (rubric #6 test #2 preview)."""
    from data.pipelines import rfp_generation as gen
    from data.pipelines.rfp_generation import (
        GeneratorContext,
        append_evaluation_history,
        build_retry_feedback,
        evaluate_section,
        should_retry_evaluation,
    )

    drafts = [
        "Generic marketing text without specific co-marketing details.",
        (
            "Brand co-marketing and exclusivity terms for Sunset Bay Resorts. "
            "This proposal presentation describes our co-branded partnership. "
            "Consistent product quality, warm customer experience, and speed of service "
            "without sacrificing quality. Offer valid for 30 days from issuance."
        ),
    ]
    call_count = {"n": 0}

    def _fake_chat(system: str, user: str) -> str:
        idx = min(call_count["n"], len(drafts) - 1)
        call_count["n"] += 1
        return drafts[idx]

    monkeypatch.setattr(gen, "_generation_available", lambda: True)
    monkeypatch.setattr(gen, "_chat_text", _fake_chat)

    ctx = GeneratorContext(
        department_id=DEPARTMENT_MARKETING,
        metadata={"client_name": "Sunset Bay"},
        key_aspects=[
            "Brand co-marketing and exclusivity terms",
            "Offer validity and proposal presentation",
        ],
    )
    key_aspects = ctx.key_aspects
    envelope = None
    iteration = 1

    while iteration <= gen.max_eval_iterations():
        if ctx.retry_feedback:
            draft = gen.generate_draft(ctx)
        else:
            draft = gen.generate_draft(ctx)
        evaluation = evaluate_section(
            department_id=ctx.department_id,
            draft_content=draft,
            key_aspects=key_aspects,
            iteration=iteration,
            use_llm_relevance=False,
        )
        if evaluation["overall_passed"]:
            envelope = append_evaluation_history(envelope, evaluation)
            break
        if not should_retry_evaluation(evaluation, iteration):
            envelope = append_evaluation_history(envelope, evaluation)
            break
        envelope = append_evaluation_history(envelope, evaluation)
        ctx.retry_feedback = build_retry_feedback(evaluation)
        iteration += 1

    assert envelope is not None
    assert envelope.latest["overall_passed"] is True
    assert envelope.latest["iteration"] == 2
    assert len(envelope.history) == 1
    assert envelope.history[0]["iteration"] == 1
    assert envelope.history[0]["overall_passed"] is False
