"""Resolve location hints for memory injection (context-26 P26-L12c)."""

from __future__ import annotations

import re
from typing import Any

from packages.shared.restaurant_locations import (
    LocationScope,
    format_location_label,
    location_short_name,
    resolve_location_hint,
    resolve_location_scope,
)

from .keys import GLOBAL_CATEGORIES

_LOCATION_SCOPED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:at|for|in)\s+[A-Za-z]", re.I),
    re.compile(r"\b(?:deliver\w*|delivery|supplier|hours?|clos\w+|open\w*)\b", re.I),
    re.compile(r"\bremember\b", re.I),
    re.compile(r"\blocal exception\b", re.I),
)


def question_needs_location_scope(question: str) -> bool:
    """True when the user message appears to be about a specific site."""
    text = (question or "").strip()
    if not text:
        return False
    if any(pattern.search(text) for pattern in _LOCATION_SCOPED_PATTERNS):
        return True
    scope = resolve_location_scope(text)
    return scope.resolved_id is not None or scope.is_ambiguous


def build_location_disambiguation_message(location_ids: tuple[int, ...]) -> str:
    """Ask the user to pick a branch when a metro name matches multiple sites."""
    labels = [location_short_name(location_id) for location_id in location_ids]
    if len(labels) == 1:
        options = labels[0]
    elif len(labels) == 2:
        options = f"{labels[0]} or {labels[1]}"
    else:
        options = ", ".join(labels[:-1]) + f", or {labels[-1]}"
    return (
        f"Several Brasaland locations match that area. "
        f"Which site do you mean — {options}? "
        "Please name the neighborhood or branch so I can answer for the correct location."
    )


def reconcile_proposal_location_id(
    proposal_location_id: int | None,
    question: str,
    *,
    category: str,
) -> int | None:
    """Resolve location from the question server-side; never rely on the user typing ids."""
    if category not in GLOBAL_CATEGORIES:
        return proposal_location_id

    scope = resolve_location_scope(question)
    if scope.resolved_id is not None:
        return scope.resolved_id
    return proposal_location_id


def resolve_injection_location_id(
    question: str,
    *,
    pending_proposal: dict[str, Any] | None = None,
) -> int | None:
    """Best-effort location_id for ``read_memory()`` from question text and pending proposal."""
    text = (question or "").strip()
    if text:
        scope = resolve_location_scope(text)
        if scope.resolved_id is not None:
            return scope.resolved_id

        from agent.tools.inventory import extract_inventory_hints

        hints = extract_inventory_hints(text)
        raw_hint = hints.get("location_id")
        if raw_hint is not None:
            try:
                return int(raw_hint)
            except (TypeError, ValueError):
                pass

    pending = pending_proposal or {}
    raw_pending = pending.get("location_id")
    if raw_pending is not None:
        try:
            return int(raw_pending)
        except (TypeError, ValueError):
            return None
    return None


def resolve_injection_scope(
    question: str,
    *,
    pending_proposal: dict[str, Any] | None = None,
) -> LocationScope:
    """Location scope for injection, falling back to a pending proposal location."""
    text = (question or "").strip()
    if text:
        scope = resolve_location_scope(text)
        if scope.resolved_id is not None or scope.is_ambiguous:
            return scope

    pending = pending_proposal or {}
    raw_pending = pending.get("location_id")
    if raw_pending is not None:
        try:
            return LocationScope(resolved_id=int(raw_pending))
        except (TypeError, ValueError):
            pass
    return LocationScope(resolved_id=None)


def format_scoped_location_instruction(location_id: int) -> str:
    """Prompt guardrail: only apply memory for the resolved location."""
    label = format_location_label(location_id)
    short = location_short_name(location_id)
    return (
        f"Location scope: {short} (location_id={location_id}, {label}). "
        f"Only use approved memory rows tagged location_id={location_id}. "
        "Do not apply memory from any other location_id. "
        "Never ask the user for a numeric location id — it is resolved server-side."
    )
