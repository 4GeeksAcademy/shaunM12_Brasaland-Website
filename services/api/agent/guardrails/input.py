"""Input guard orchestration (context-25 P25-L12 evaluation order)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from agent.classify import has_brasaland_domain_signals

from .casual import is_casual_off_domain
from .patterns_security import is_authenticated_write_command, is_instruction_override
from .personal_use import assess_general_assistant_task, primary_personal_reason

GuardAction = Literal["continue", "block"]
FailureType = Literal["security", "content"]


@dataclass(frozen=True)
class GuardInputResult:
    """Result of ``evaluate_input_guard()`` (P25-L11–L12)."""

    action: GuardAction
    failure_type: FailureType | None = None
    reason: str | None = None
    redirect_required: bool = False
    matched: list[str] = field(default_factory=list)
    personal_use_score: float | None = None


def evaluate_input_guard(question: str) -> GuardInputResult:
    """Evaluate Tier 0–2 input guardrails in locked order (P25-L12)."""
    text = (question or "").strip()
    if not text:
        return GuardInputResult(action="continue")

    # 1. instruction_override AND NOT write_exempt → block (security)
    if is_instruction_override(text) and not is_authenticated_write_command(text):
        return GuardInputResult(
            action="block",
            failure_type="security",
            reason="instruction_override",
            matched=["instruction_override"],
        )

    casual = is_casual_off_domain(text)

    # 2. has_brasaland_domain_signals → continue (redirect if casual)
    if has_brasaland_domain_signals(text):
        matched = ["domain_allowlist"]
        if casual:
            matched.append("casual_off_domain")
        return GuardInputResult(
            action="continue",
            redirect_required=casual,
            matched=matched,
        )

    # 3. personal_use score ≥ threshold (off-domain) → block (content)
    assessment = assess_general_assistant_task(text)
    if assessment.should_block:
        return GuardInputResult(
            action="block",
            failure_type="content",
            reason=primary_personal_reason(assessment),
            matched=list(assessment.signals),
            personal_use_score=assessment.score,
        )

    # 4. is_casual_off_domain → continue + redirect_required
    if casual:
        return GuardInputResult(
            action="continue",
            redirect_required=True,
            matched=["casual_off_domain"],
        )

    # 5. default → continue
    return GuardInputResult(action="continue")
