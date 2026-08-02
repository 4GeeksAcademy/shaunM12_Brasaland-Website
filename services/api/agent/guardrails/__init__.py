"""Support Agent guardrails package (context-25 SEC-114).

Phase scaffold:
  P25-0 — this package + locked message templates
  P25-1 — prompts (``prompts.py``, ``data/pipelines/prompt_security.py``)
  P25-2 — input guard (``input.py``, patterns, classify allowlist)
  P25-3 — sanitization (``sanitize.py``)
  P25-4 — output validation (``output.py``)
  P25-5 — observability logging (``observability.py``)
  P25-6 — graph wiring + full test suite

Authority: memory-bank/historical-reference/context-25-securing-agents-harness-guardrails.md
"""

from __future__ import annotations

from .input import GuardInputResult, evaluate_input_guard
from .messages import (
    CASUAL_REPLY_MESSAGE,
    INSTRUCTION_OVERRIDE_REFUSAL,
    OUTPUT_VALIDATION_FALLBACK,
    REDIRECT_SUFFIX,
    REFUSAL_SUPPORT_REDIRECT_SUFFIX,
    answer_has_redirect_marker,
    enforce_redirect_suffix,
    resolve_guard_block_message,
)
from .observability import get_guardrail_summary, question_hash_prefix, record_guardrail_event
from .output import OutputValidationResult, validate_agent_output
from .personal_use import GeneralTaskAssessment, block_threshold, family_block_threshold

__all__ = [
    "CASUAL_REPLY_MESSAGE",
    "GuardInputResult",
    "GeneralTaskAssessment",
    "INSTRUCTION_OVERRIDE_REFUSAL",
    "OUTPUT_VALIDATION_FALLBACK",
    "OutputValidationResult",
    "REDIRECT_SUFFIX",
    "REFUSAL_SUPPORT_REDIRECT_SUFFIX",
    "answer_has_redirect_marker",
    "block_threshold",
    "enforce_redirect_suffix",
    "evaluate_input_guard",
    "family_block_threshold",
    "get_guardrail_summary",
    "question_hash_prefix",
    "record_guardrail_event",
    "resolve_guard_block_message",
    "validate_agent_output",
]
