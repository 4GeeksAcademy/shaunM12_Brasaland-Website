"""Infer memory proposals when the LLM asks to remember but omits memory_proposal (context-26)."""

from __future__ import annotations

import re

from packages.shared.restaurant_locations import resolve_location_scope

from .correction_intent import looks_like_memory_correction
from .schemas import MemoryProposal, ProposalValidationError, validate_proposal_shape

_ANSWER_PROPOSAL_PROMPT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"would you like me to (?:remember|update|store|save|confirm)", re.I),
    re.compile(r"would you like to (?:remember|update|store|save|confirm)", re.I),
    re.compile(r"do you want me to (?:remember|update|store|save|confirm)", re.I),
    re.compile(r"want me to remember", re.I),
    re.compile(r"\bupdate the memory\b", re.I),
    re.compile(r"\bremember (?:this|that|it) for next time\b", re.I),
    re.compile(r"shall I (?:remember|update|store|save|confirm)", re.I),
    re.compile(r"should I (?:remember|update|store|save|confirm)", re.I),
    re.compile(r"\bconfirm (?:this|that|the) (?:change|correction|update|memory)\b", re.I),
)

_LOCATION_ID_IN_TEXT = re.compile(r"location_id\s*[=:]\s*(\d+)", re.I)

_WEEKDAY_PATTERN = re.compile(
    r"\b("
    r"monday|tuesdays?|wednesdays?|thursdays?|friday|fridays?|saturdays?|sundays?"
    r")\b",
    re.I,
)

_SUPPLIER_KEY_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"\bmeat\b", re.I),
        "meat_delivery_day",
        "Meat supplier delivers on {day}",
    ),
    (
        re.compile(r"\b(?:vegetable|vegetables|produce|fruit)\b", re.I),
        "vegetable_delivery_day",
        "Vegetable supplier delivers on {day}",
    ),
    (
        re.compile(r"\b(?:general|supplier|deliver\w*)\b", re.I),
        "general_delivery_day",
        "General supplier delivers on {day}",
    ),
)

_DAY_TITLE: dict[str, str] = {
    "monday": "Monday",
    "mondays": "Monday",
    "tuesday": "Tuesday",
    "tuesdays": "Tuesday",
    "wednesday": "Wednesday",
    "wednesdays": "Wednesday",
    "thursday": "Thursday",
    "thursdays": "Thursday",
    "friday": "Friday",
    "fridays": "Friday",
    "saturday": "Saturday",
    "saturdays": "Saturday",
    "sunday": "Sunday",
    "sundays": "Sunday",
}

_TIME_PATTERN = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
    re.I,
)
_WEEKEND_PATTERN = re.compile(r"\bweekend\b", re.I)
_FRIDAY_PATTERN = re.compile(r"\bfridays?\b", re.I)
_HOURS_CLOSE_PATTERN = re.compile(r"\b(?:close|closing|closes)\b", re.I)
_HOURS_OPEN_PATTERN = re.compile(r"\b(?:open|opening|opens)\b", re.I)


def answer_solicits_memory_confirmation(answer: str) -> bool:
    """True when the model answer asks the user to confirm a memory write."""
    text = (answer or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in _ANSWER_PROPOSAL_PROMPT_PATTERNS)


def _normalize_day(raw: str) -> str | None:
    cleaned = (raw or "").strip().lower()
    return _DAY_TITLE.get(cleaned)


def _preferred_delivery_day(*texts: str) -> str | None:
    """Pick the corrected day (before 'not') when present, else the first weekday."""
    for text in texts:
        if not text:
            continue
        not_split = re.split(r"\bnot\b", text, maxsplit=1, flags=re.I)
        preferred_segment = not_split[0]
        match = _WEEKDAY_PATTERN.search(preferred_segment)
        if match:
            day = _normalize_day(match.group(1))
            if day:
                return day
    for text in texts:
        match = _WEEKDAY_PATTERN.search(text or "")
        if match:
            day = _normalize_day(match.group(1))
            if day:
                return day
    return None


def _resolve_location_id(question: str, answer: str) -> int | None:
    for text in (answer, question):
        match = _LOCATION_ID_IN_TEXT.search(text or "")
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
    for text in (question, answer):
        scope = resolve_location_scope(text or "")
        if scope.resolved_id is not None:
            return scope.resolved_id
    return None


def _format_time(hour: str, minute: str | None, meridiem: str) -> str:
    hh = int(hour)
    mm = minute or "00"
    if mm == "00":
        return f"{hh}{meridiem.lower()}"
    return f"{hh}:{mm}{meridiem.lower()}"


def _preferred_time(*texts: str) -> str | None:
    """Pick the corrected clock time (before 'not') when present."""
    for text in texts:
        if not text:
            continue
        not_split = re.split(r"\bnot\b", text, maxsplit=1, flags=re.I)
        preferred_segment = not_split[0]
        match = _TIME_PATTERN.search(preferred_segment)
        if match:
            return _format_time(match.group(1), match.group(2), match.group(3))
    for text in texts:
        match = _TIME_PATTERN.search(text or "")
        if match:
            return _format_time(match.group(1), match.group(2), match.group(3))
    return None


def _hours_proposal_fields(question: str, answer: str, *, clock: str) -> tuple[str, str] | None:
    combined = f"{question}\n{answer}"
    if not (_HOURS_CLOSE_PATTERN.search(combined) or _HOURS_OPEN_PATTERN.search(combined)):
        return None

    if _WEEKEND_PATTERN.search(combined):
        if _HOURS_CLOSE_PATTERN.search(combined):
            return "weekend_close", f"Weekend closing time is {clock}"
        return "weekend_open", f"Weekend opening time is {clock}"

    if _FRIDAY_PATTERN.search(combined):
        if _HOURS_CLOSE_PATTERN.search(combined):
            return "friday_close", f"Friday closing time is {clock}"
        return "weekday_open", f"Friday opening time is {clock}"

    if _HOURS_CLOSE_PATTERN.search(combined):
        return "weekday_close", f"Weekday closing time is {clock}"
    return "weekday_open", f"Weekday opening time is {clock}"


def _supplier_proposal_fields(question: str, answer: str, *, day: str) -> tuple[str, str] | None:
    combined = f"{question}\n{answer}"
    for pattern, key, template in _SUPPLIER_KEY_RULES:
        if pattern.search(combined):
            return key, template.format(day=day)
    return None


def infer_memory_proposal(
    question: str,
    *,
    answer: str = "",
) -> MemoryProposal | None:
    """Build a proposal from correction text when the LLM omitted JSON."""
    if not looks_like_memory_correction(question) and not answer_solicits_memory_confirmation(
        answer
    ):
        return None

    location_id = _resolve_location_id(question, answer)
    if location_id is None:
        return None

    day = _preferred_delivery_day(question, answer)
    if day is not None:
        supplier_fields = _supplier_proposal_fields(question, answer, day=day)
        if supplier_fields is not None:
            key, value = supplier_fields
            return MemoryProposal(
                location_id=location_id,
                category="suppliers",
                key=key,
                value=value,
                reason="User correction",
            )

    clock = _preferred_time(question, answer)
    if clock is not None:
        hours_fields = _hours_proposal_fields(question, answer, clock=clock)
        if hours_fields is not None:
            key, value = hours_fields
            return MemoryProposal(
                location_id=location_id,
                category="hours",
                key=key,
                value=value,
                reason="User correction",
            )

    return None


def infer_validated_memory_proposal(
    question: str,
    *,
    answer: str = "",
) -> MemoryProposal | None:
    """Infer and validate a proposal; return None when inference or validation fails."""
    inferred = infer_memory_proposal(question, answer=answer)
    if inferred is None:
        return None
    try:
        return validate_proposal_shape(inferred, question=question)
    except ProposalValidationError:
        return None
