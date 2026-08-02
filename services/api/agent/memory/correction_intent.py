"""Detect user messages that share a local operational correction (context-26)."""

from __future__ import annotations

import re

MEMORY_CORRECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bremember\b.*\b(?:for next time|that|this|it)\b", re.I),
    re.compile(r"\b(?:can you|could you|please)\b.*\bremember\b", re.I),
    re.compile(r"\bnote that\b", re.I),
    re.compile(r"\bnot\b.+\b(?:manual|procedure|standard|policy|kb)\b", re.I),
    re.compile(
        r"\bon\s+\w+days?\s*,\s*not\s+\w+days?\b",
        re.I,
    ),
    re.compile(
        r"\b(?:closes?|closing|deliver\w*|delivery|open\w*)\b.+\bnot\b",
        re.I,
    ),
    re.compile(r"\b(?:actually|correction)\b", re.I),
    re.compile(r"\blocal exception\b", re.I),
    re.compile(r"\blocal practice\b", re.I),
    re.compile(r"\bour (?:location|site|branch)\b", re.I),
)


def looks_like_memory_correction(question: str) -> bool:
    """True when the user appears to offer a recurring local ops correction."""
    text = (question or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in MEMORY_CORRECTION_PATTERNS)


def user_requests_memory_storage(question: str) -> bool:
    """True when the user explicitly asks to remember a local fact."""
    text = (question or "").strip()
    if not text:
        return False
    explicit = (
        re.search(r"\bremember\b.*\b(?:for next time|that|this|it)\b", text, re.I),
        re.search(r"\b(?:can you|could you|please)\b.*\bremember\b", text, re.I),
        re.search(r"\blocal exception\b", text, re.I),
        re.search(r"\bstore (?:that|this|it)\b", text, re.I),
    )
    return any(match for match in explicit if match)


def user_wants_memory_proposal(question: str) -> bool:
    """True when this turn should be allowed to stage a new memory proposal."""
    return looks_like_memory_correction(question) or user_requests_memory_storage(question)


_MEMORY_CONFIRMATION_SUFFIX = re.compile(
    r"(?:\n\n|\.\s+|\?\s+)"
    r"(?:Would you like me to|Should I|Do you want me to|Shall I|Want me to)"
    r"[^.?\n]{0,220}\?\s*$",
    re.I,
)


def strip_memory_confirmation_ask(answer: str) -> str:
    """Remove trailing remember/update prompts on read-only turns."""
    cleaned = (answer or "").strip()
    if not cleaned:
        return cleaned
    stripped = _MEMORY_CONFIRMATION_SUFFIX.sub("", cleaned).strip()
    return stripped or cleaned
