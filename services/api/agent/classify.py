"""Rule-based question classifier for Support Agent routing (P2-L13–L22)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from incidents.constants import BRANCH_LABELS, BRANCH_VALUES, ORIGIN_VALUES, STATUS_VALUES

Intent = Literal["rag", "incident", "inventory", "both"]

INCIDENT_NOUNS: tuple[str, ...] = (
    "incident",
    "ticket",
    "case",
    "complaint",
    "report",
)

STATUS_PHRASES: tuple[tuple[str, str], ...] = (
    ("in progress", "in_progress"),
    ("in_progress", "in_progress"),
    ("open", "open"),
    ("resolved", "resolved"),
    ("discarded", "discarded"),
)

KB_SIGNALS: tuple[str, ...] = (
    "policy",
    "policies",
    "manual",
    "procedure",
    "procedures",
    "knowledge base",
    "guidelines",
    "loyalty",
    "points",
    "tier",
    "gold",
    "silver",
    "bronze",
    "rewards",
    "allergen",
    "allergens",
    "waste",
    "waste policy",
    "supplier manual",
    "food safety",
    "training",
    "onboarding",
    "handbook",
)

INVENTORY_SIGNALS: tuple[str, ...] = (
    "stock",
    "current stock",
    "in stock",
    "out of stock",
    "low stock",
    "inventory",
    "sku",
    "reorder",
    "restock",
    "threshold",
    "minimum stock",
    "min stock",
    "below minimum",
)

GENERIC_ISSUE_WORDS: frozenset[str] = frozenset({"issue", "problem", "help", "error"})

_INCIDENT_ID_RE = re.compile(r"\bincident\s+#?(\d+)\b", re.IGNORECASE)
_HASH_ID_RE = re.compile(r"#(\d+)\b")


@dataclass(frozen=True)
class ClassifyResult:
    intent: Intent
    incident_id: int | None = None
    incident_filters: dict[str, str] = field(default_factory=dict)
    matched: list[str] = field(default_factory=list)


def classify_question(question: str) -> ClassifyResult:
    """Pure rule-based intent classification — no HTTP, RAG, or LLM (P2-L22)."""
    text = (question or "").strip()
    matched: list[str] = []

    has_incident = _has_incident_signals(text, matched)
    has_kb = _has_kb_signals(text, matched)
    has_inventory = _has_inventory_signals(text, matched)

    incident_id = _extract_incident_id(text, has_incident)
    incident_filters = _extract_incident_filters(text, matched, incident_id)

    if has_incident and has_kb:
        intent: Intent = "both"
        matched.append("intent:both")
    elif has_incident:
        intent = "incident"
        matched.append("intent:incident")
    elif has_inventory:
        intent = "inventory"
        matched.append("intent:inventory")
    else:
        intent = "rag"
        matched.append("intent:rag")

    return ClassifyResult(
        intent=intent,
        incident_id=incident_id,
        incident_filters=incident_filters,
        matched=matched,
    )


def _contains_phrase(text: str, phrase: str) -> bool:
    if " " in phrase:
        return phrase in text
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def _has_incident_signals(text: str, matched: list[str]) -> bool:
    lower = text.lower()

    for noun in INCIDENT_NOUNS:
        if _contains_phrase(lower, noun):
            matched.append(noun)
            return True

    if _INCIDENT_ID_RE.search(text) or (
        _HASH_ID_RE.search(text) and any(_contains_phrase(lower, n) for n in INCIDENT_NOUNS)
    ):
        matched.append("incident_id_pattern")
        return True

    for branch in BRANCH_VALUES:
        pattern = branch.replace("_", " ")
        if _contains_phrase(lower, pattern) or _contains_phrase(lower, branch):
            matched.append(f"branch:{branch}")
            return True

    for _key, label in BRANCH_LABELS.items():
        if _contains_phrase(lower, label.lower()):
            matched.append(f"branch_label:{label}")
            return True

    for status_phrase, status_value in STATUS_PHRASES:
        if _contains_phrase(lower, status_phrase):
            matched.append(f"status:{status_value}")
            return True

    for origin in ORIGIN_VALUES:
        if _contains_phrase(lower, origin):
            matched.append(f"origin:{origin}")
            return True

    if any(_contains_phrase(lower, word) for word in GENERIC_ISSUE_WORDS):
        return False

    return False


def _has_kb_signals(text: str, matched: list[str]) -> bool:
    lower = text.lower()
    for signal in KB_SIGNALS:
        if _contains_phrase(lower, signal):
            matched.append(f"kb:{signal}")
            return True
    return False


def _has_inventory_signals(text: str, matched: list[str]) -> bool:
    lower = text.lower()
    # Longer phrases first to avoid partial matches.
    for signal in sorted(INVENTORY_SIGNALS, key=len, reverse=True):
        if _contains_phrase(lower, signal):
            matched.append(f"inventory:{signal}")
            return True
    return False


def _extract_incident_id(text: str, has_incident: bool) -> int | None:
    match = _INCIDENT_ID_RE.search(text)
    if match:
        return int(match.group(1))
    if has_incident:
        hash_match = _HASH_ID_RE.search(text)
        if hash_match:
            return int(hash_match.group(1))
    return None


def _extract_incident_filters(
    text: str,
    matched: list[str],
    incident_id: int | None,
) -> dict[str, str]:
    if incident_id is not None:
        return {}

    lower = text.lower()
    filters: dict[str, str] = {}

    for status_phrase, status_value in STATUS_PHRASES:
        if _contains_phrase(lower, status_phrase):
            filters["status"] = status_value
            matched.append(f"filter_status:{status_value}")
            break

    for origin in ORIGIN_VALUES:
        if _contains_phrase(lower, origin):
            filters["origin"] = origin
            matched.append(f"filter_origin:{origin}")
            break

    for branch in BRANCH_VALUES:
        pattern = branch.replace("_", " ")
        if _contains_phrase(lower, pattern) or _contains_phrase(lower, branch):
            filters["branch"] = branch
            matched.append(f"filter_branch:{branch}")
            break
    else:
        for key, label in BRANCH_LABELS.items():
            if _contains_phrase(lower, label.lower()):
                filters["branch"] = key
                matched.append(f"filter_branch:{key}")
                break

    return filters
