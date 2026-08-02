"""Rule-first classifier for pending memory proposals (context-26 P26-L9)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from .patterns_proposal import (
    APPROVE_MEMORY_PATTERNS,
    APPROVE_PREFIX_RE,
    BARE_ASSENT_PHRASES,
    CONTINUATION_SPLIT_RE,
    EDIT_PATTERNS,
    REJECT_PATTERNS,
)

ProposalOutcome = Literal["approve", "reject", "edit", "ambiguous"]

DEFAULT_PENDING_TTL_HOURS = 24


def pending_ttl_hours() -> int:
    raw = os.getenv("AGENT_MEMORY_PENDING_TTL_HOURS", "").strip()
    if not raw:
        return DEFAULT_PENDING_TTL_HOURS
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_PENDING_TTL_HOURS


def _normalize_assent(text: str) -> str:
    cleaned = re.sub(r"[^\w\s']", " ", text.lower())
    return " ".join(cleaned.split())


def is_bare_assent(text: str) -> bool:
    normalized = _normalize_assent(text)
    if not normalized:
        return True
    return normalized in BARE_ASSENT_PHRASES


def matches_reject(text: str) -> bool:
    return any(pattern.search(text) for pattern in REJECT_PATTERNS)


def matches_approve_with_memory_intent(text: str) -> bool:
    return any(pattern.search(text) for pattern in APPROVE_MEMORY_PATTERNS)


def extract_edit_value(text: str) -> str | None:
    for pattern in EDIT_PATTERNS:
        match = pattern.search(text.strip())
        if match:
            value = (match.group("value") or "").strip(" .")
            if value:
                return value
    return None


def extract_continued_question(text: str) -> str | None:
    """Return operational remainder after memory assent, or None if approve-only."""
    stripped = text.strip()
    if not stripped:
        return None

    parts = CONTINUATION_SPLIT_RE.split(stripped, maxsplit=1)
    candidate = parts[-1].strip() if len(parts) > 1 else stripped
    candidate = APPROVE_PREFIX_RE.sub("", candidate, count=1).strip(" ,.-—–")
    if not candidate or is_bare_assent(candidate):
        return None
    if matches_approve_with_memory_intent(candidate) and len(parts) == 1:
        return None
    return candidate


@dataclass(frozen=True)
class ProposalResolution:
    outcome: ProposalOutcome
    reason: str | None = None
    continued_question: str | None = None
    edited_value: str | None = None


def pending_is_expired(pending_at: str | None, *, now: datetime | None = None) -> bool:
    if not pending_at:
        return False
    try:
        parsed = datetime.fromisoformat(pending_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return current - parsed > timedelta(hours=pending_ttl_hours())


def classify_memory_decision(message: str, *, pending: dict[str, Any] | None = None) -> ProposalResolution:
    """Classify user reply to a pending proposal (P26-L9c order: reject → edit → approve → ambiguous)."""
    _ = pending
    text = (message or "").strip()
    if not text:
        return ProposalResolution(outcome="ambiguous", reason="empty_reply")

    if matches_reject(text):
        return ProposalResolution(outcome="reject", reason="user_declined")

    edited_value = extract_edit_value(text)
    if edited_value:
        continued = extract_continued_question(text)
        return ProposalResolution(
            outcome="edit",
            reason="user_edited_value",
            edited_value=edited_value,
            continued_question=continued,
        )

    if matches_approve_with_memory_intent(text):
        continued = extract_continued_question(text)
        return ProposalResolution(outcome="approve", continued_question=continued)

    if is_bare_assent(text):
        return ProposalResolution(outcome="ambiguous", reason="bare_assent")

    from agent.classify import looks_like_live_ops_question

    if looks_like_live_ops_question(text):
        return ProposalResolution(outcome="ambiguous", reason="topic_change")

    return ProposalResolution(outcome="ambiguous", reason="no_memory_intent")


def should_continue_after_ambiguous_pending_resolution(
    resolution: ProposalResolution,
    question: str,
) -> bool:
    """True when a pending proposal should be cleared and the new question handled normally."""
    if resolution.outcome != "ambiguous":
        return False
    if resolution.reason == "topic_change":
        return True
    if resolution.reason == "no_memory_intent":
        from .correction_intent import looks_like_memory_correction

        return looks_like_memory_correction(question)
    return False
