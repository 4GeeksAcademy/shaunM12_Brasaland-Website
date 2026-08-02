"""Rule patterns for memory proposal user responses (context-26 P26-L9)."""

from __future__ import annotations

import re

BARE_ASSENT_PHRASES: frozenset[str] = frozenset(
    {"yes", "y", "ok", "okay", "sure", "yep", "yeah", "fine", "correct"}
)

EDIT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:remember|save|store)\b.*\b(?:as|it as)\b\s*(?P<value>.+)$",
        re.I,
    ),
    re.compile(r"\bactually\b[:\-]?\s*(?P<value>.+)$", re.I),
)

APPROVE_MEMORY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:yes|yeah|yep|sure|ok(?:ay)?|please)\b.*\bremember\b", re.I),
    re.compile(r"\bremember\b.*\b(?:that|this|it)\b", re.I),
    re.compile(r"\b(?:save|store)\b.*\b(?:that|this|it)\b", re.I),
    re.compile(r"\bgo ahead\b.*\b(?:remember|save)\b", re.I),
    re.compile(r"\b(?:yes|yeah)\b.*\b(?:save|store)\b", re.I),
    re.compile(r"\b(?:sí|si)\b.*\b(?:recuerda|recuerde|guarda)\b", re.I),
    re.compile(r"\b(?:recuerda|recuerde)\b.*\b(?:eso|esto)\b", re.I),
)

REJECT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:no|nope|nah)\b", re.I),
    re.compile(r"\bdon'?t\b.*\b(?:remember|save|store)\b", re.I),
    re.compile(r"\b(?:skip|forget)\b.*\b(?:memory|that)\b", re.I),
    re.compile(r"\bnot now\b", re.I),
    re.compile(r"\bno\b.*\b(?:guardes|recuerdes)\b", re.I),
)

APPROVE_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"(?:yes|yeah|yep|sure|ok(?:ay)?|please)[,\s\-—–]*"
    r"(?:remember(?:\s+(?:that|this|it))?|save(?:\s+(?:that|this|it))?|store(?:\s+(?:that|this|it))?)"
    r"|remember(?:\s+(?:that|this|it))?"
    r"|go ahead(?:\s+and)?\s+(?:remember|save)"
    r")\b[,\s\-—–]*",
    re.I,
)

CONTINUATION_SPLIT_RE = re.compile(r"[\—\-–]+|\.\s+|\band then\b", re.I)
