"""P25-0 scaffold tests — locked templates and package imports."""

from __future__ import annotations

import pytest

from agent.guardrails.messages import (
    CASUAL_REPLY_MESSAGE,
    INSTRUCTION_OVERRIDE_REFUSAL,
    OUTPUT_VALIDATION_FALLBACK,
    REDIRECT_SUFFIX,
    answer_has_redirect_marker,
    enforce_redirect_suffix,
    resolve_guard_block_message,
)
from agent.guardrails.personal_use import block_threshold, family_block_threshold


def test_casual_reply_message_includes_acknowledgment_and_redirect():
    assert "live weather" in CASUAL_REPLY_MESSAGE.lower()
    assert "brasaland" in CASUAL_REPLY_MESSAGE.lower()
    assert "support agent" in CASUAL_REPLY_MESSAGE.lower()


def test_redirect_suffix_dedup():
    assert answer_has_redirect_marker("Ask Brasaland support about incidents.")
    assert not answer_has_redirect_marker("Hello there.")

    updated, reason = enforce_redirect_suffix("Hello there.")
    assert reason == "domain_redirect:suffix_appended"
    assert updated.endswith(REDIRECT_SUFFIX.strip())

    unchanged, already = enforce_redirect_suffix("Contact Brasaland support.")
    assert unchanged == "Contact Brasaland support."
    assert already == "domain_redirect:already_present"


def test_resolve_guard_block_security_vs_personal():
    assert (
        resolve_guard_block_message({"failure_type": "security"})
        == INSTRUCTION_OVERRIDE_REFUSAL
    )
    personal = resolve_guard_block_message(
        {"failure_type": "content", "guardrail_reason": "personal_use:academic"}
    )
    assert "homework" in personal.lower() or "academic" in personal.lower()


def test_output_validation_fallback_copy():
    assert "safely" in OUTPUT_VALIDATION_FALLBACK.lower()
    assert "brasaland" in OUTPUT_VALIDATION_FALLBACK.lower()


def test_threshold_defaults():
    assert block_threshold() == 0.55
    assert family_block_threshold() == 0.50


def test_evaluate_input_guard_continues_for_kb_question():
    from agent.guardrails.input import evaluate_input_guard

    result = evaluate_input_guard("How many points for Gold tier?")
    assert result.action == "continue"
    assert result.failure_type is None
