"""Casual / off-domain detection (context-25 P25-L4, P25-L12)."""

from __future__ import annotations

import re

CASUAL_OFF_DOMAIN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bwhat(?:'s| is) the weather\b", re.I),
    re.compile(r"\bweather in\b", re.I),
    re.compile(r"\bwhat time is it in\b", re.I),
    re.compile(r"\btime in (?:tokyo|london|paris|new york)\b", re.I),
    re.compile(r"^(?:hi|hello|hey|good morning|good afternoon)\b", re.I),
    re.compile(r"\bhow are you\b", re.I),
    re.compile(r"\bwhat(?:'s| is) the capital of\b", re.I),
    re.compile(r"\bwho won (?:the|a) \w+\b", re.I),
)

SMALL_TALK_MAX_WORDS = 8


def is_casual_off_domain(text: str) -> bool:
    """True for brief small talk or general trivia — answer allowed with redirect."""
    stripped = (text or "").strip()
    if not stripped:
        return False
    if any(pattern.search(stripped) for pattern in CASUAL_OFF_DOMAIN_PATTERNS):
        return True
    words = stripped.split()
    if len(words) <= SMALL_TALK_MAX_WORDS and re.match(
        r"^(?:hi|hello|hey|thanks|thank you|goodbye|bye)\b",
        stripped,
        re.I,
    ):
        return True
    return False
