"""Instruction-override patterns — Tier 1 security (context-25 P25-L15)."""

from __future__ import annotations

import re

from agent.classify import (
    _CREATE_RE,
    _INSTRUCTIVE_CREATE_RE,
    _UPDATE_RE,
    _UPDATE_TO_RE,
    _has_inventory_write_signals,
)

INSTRUCTION_OVERRIDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(?:your\s+)?(?:previous\s+)?instructions", re.I),
    re.compile(r"forget\s+(?:that\s+)?(?:you\s+)?(?:work\s+for|are)", re.I),
    re.compile(
        r"(?:you\s+are\s+now|act\s+as\s+if\s+you\s+(?:have|had)\s+no)\s+rules",
        re.I,
    ),
    re.compile(r"disregard\s+(?:your\s+)?(?:system\s+)?prompt", re.I),
    re.compile(r"pretend\s+(?:you\s+)?(?:have\s+)?no\s+(?:rules|restrictions)", re.I),
    re.compile(r"new\s+instructions\s*:", re.I),
    re.compile(r"^\s*system\s*:", re.I),
    re.compile(
        r"\boverride\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions)\b",
        re.I,
    ),
)


def is_instruction_override(text: str) -> bool:
    """True when the user attempts to replace system instructions (P25-L15c: full string)."""
    return any(pattern.search(text) for pattern in INSTRUCTION_OVERRIDE_PATTERNS)


def is_authenticated_write_command(text: str) -> bool:
    """Imperative ops writes exempt from jailbreak block (P25-L15b)."""
    if _INSTRUCTIVE_CREATE_RE.search(text):
        return False
    if _CREATE_RE.search(text):
        return True
    if _UPDATE_RE.search(text) or _UPDATE_TO_RE.search(text):
        return True
    scratch: list[str] = []
    if _has_inventory_write_signals(text, scratch):
        return True
    return False
