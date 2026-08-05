"""Memory denylist — proposal and write gates (context-26 P26-L2)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent.guardrails.patterns_security import is_instruction_override

from .keys import GLOBAL_CATEGORIES, MemoryKeyError, validate_category

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?:\+57|\+1|\(\d{3}\))\s*\d")

PAYROLL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:payroll|salary|wage|compensation|n[oó]mina)\b", re.I),
    re.compile(r"\b(?:hourly\s+rate|tips?\s+allocation)\b", re.I),
)

ZERO_RISK_ALLERGEN = re.compile(r"\bzero\s+risk\b", re.I)

LIVE_METRICS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:current\s+stock|stock\s+level|open\s+incident\s+count)\b", re.I),
    re.compile(r"\b(?:yesterday(?:'s)?\s+average\s+ticket|live\s+sales)\b", re.I),
)

BRASA_POINTS_PII = re.compile(
    r"\b(?:brasa\s+points?\s+(?:balance|email|phone|member)|loyalty\s+(?:email|phone))\b",
    re.I,
)


@dataclass(frozen=True)
class DenylistResult:
    blocked: bool
    reason: str | None = None


def check_denylist(*, category: str, value: str, reason: str | None = None) -> DenylistResult:
    """Return blocked=True when text or category must not enter memory."""
    text = " ".join(part for part in (value, reason or "") if part).strip()
    if not text:
        return DenylistResult(blocked=True, reason="empty_value")

    try:
        validate_category(category)
    except MemoryKeyError:
        return DenylistResult(blocked=True, reason="invalid_category")

    if is_instruction_override(text):
        return DenylistResult(blocked=True, reason="instruction_override")

    if ZERO_RISK_ALLERGEN.search(text):
        return DenylistResult(blocked=True, reason="allergen_zero_risk")

    if BRASA_POINTS_PII.search(text):
        return DenylistResult(blocked=True, reason="brasa_points_pii")

    if EMAIL_PATTERN.search(text):
        return DenylistResult(blocked=True, reason="email_pii")

    if PHONE_PATTERN.search(text):
        return DenylistResult(blocked=True, reason="phone_pii")

    for pattern in PAYROLL_PATTERNS:
        if pattern.search(text):
            return DenylistResult(blocked=True, reason="payroll")

    for pattern in LIVE_METRICS_PATTERNS:
        if pattern.search(text):
            return DenylistResult(blocked=True, reason="live_operational_snapshot")

    return DenylistResult(blocked=False)


def requires_location_id(category: str) -> bool:
    return validate_category(category) in GLOBAL_CATEGORIES
