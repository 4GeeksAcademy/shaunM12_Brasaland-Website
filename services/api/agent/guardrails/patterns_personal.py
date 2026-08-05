"""General-assistant task family patterns (context-25 P25-L11c)."""

from __future__ import annotations

import re

PERSONAL_TASK_FAMILIES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b(?:write|draft|compose|create|generate|produce)\s+"
            r"(?:me\s+)?(?:a\s+|an\s+|my\s+)?"
            r"(?:essay|poem|story|song|article|blog|script|novel|speech|letter|email)\b",
            re.I,
        ),
        "creative",
    ),
    (
        re.compile(
            r"\b(?:homework|assignment|coursework|thesis|dissertation|exam prep|school project)\b",
            re.I,
        ),
        "academic",
    ),
    (
        re.compile(
            r"\b(?:help\s+me\s+with\s+my\s+(?:homework|assignment|coursework|thesis))\b",
            re.I,
        ),
        "academic",
    ),
    (
        re.compile(
            r"\b(?:act\s+as|be)\s+my\s+(?:therapist|counselor|life coach|psychologist)\b",
            re.I,
        ),
        "wellness",
    ),
    (
        re.compile(
            r"\b(?:relationship advice|mental health advice|breakup advice)\b",
            re.I,
        ),
        "wellness",
    ),
    (
        re.compile(
            r"\b(?:debug|code|program|script|implement)\b.*\b(?:personal|side)\s+project\b",
            re.I,
        ),
        "personal_code",
    ),
    (
        re.compile(
            r"\b(?:my\s+resume|cover letter|job application|interview prep)\b",
            re.I,
        ),
        "personal_career",
    ),
    (
        re.compile(
            r"\b(?:do\s+my|complete\s+my|finish\s+my)\s+"
            r"(?:homework|assignment|coursework|project)\b",
            re.I,
        ),
        "academic",
    ),
    (
        re.compile(
            r"\b(?:translate|proofread|rewrite|edit)\s+(?:this\s+)?"
            r"(?:love\s+)?(?:letter|message|text|email)\b",
            re.I,
        ),
        "personal_media",
    ),
    (
        re.compile(
            r"\b(?:tell me a joke|play a game|roleplay as|dungeon master)\b",
            re.I,
        ),
        "entertainment",
    ),
    (
        re.compile(
            r"\b(?:plan my trip|vacation itinerary|travel itinerary)\b",
            re.I,
        ),
        "concierge",
    ),
    (
        re.compile(
            r"\b(?:explain|teach me about|tell me about)\s+"
            r"(?:the\s+)?(?:history of|quantum|philosophy of|life of)\b",
            re.I,
        ),
        "general_knowledge",
    ),
)

DELIVERABLE_REQUEST = re.compile(
    r"\b(?:write|draft|compose|create|generate|produce|build|make|code|program|debug|solve|complete|finish)\s+"
    r"(?:me\s+)?(?:a\s+|an\s+|my\s+)?\w+",
    re.I,
)

TASK_DELEGATION = re.compile(
    r"\b(?:help\s+me|can you|could you|please|i need you to)\s+(?:to\s+)?"
    r"(?:write|do|make|create|solve|explain|translate|proofread|debug|finish|complete)\b",
    re.I,
)

PERSONAL_POSSESSIVE = re.compile(
    r"\bmy\s+(?:homework|essay|assignment|project|resume|thesis|relationship|breakup)\b",
    re.I,
)

ROLEPLAY_REQUEST = re.compile(
    r"\b(?:act as|you are now|pretend (?:to be|you(?:'re| are)))\s+",
    re.I,
)
