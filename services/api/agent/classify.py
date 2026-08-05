"""Rule-based question classifier for Support Agent routing (P2-L13–L22, P24-3b)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from incidents.constants import (
    BRANCH_LABELS,
    BRANCH_VALUES,
    CATEGORY_VALUES,
    ORIGIN_VALUES,
    STATUS_VALUES,
)
from packages.shared.incidents_validation import LEGACY_CATEGORY_MAP

Intent = Literal["rag", "incident", "inventory", "both", "incident_write", "inventory_write"]
IncidentAction = Literal["list", "get", "summary"]
WriteAction = Literal["create", "update_status"]

INCIDENT_NOUNS: tuple[str, ...] = (
    "incident",
    "ticket",
    "case",
    "complaint",
    "report",
)

INCIDENT_NOUN_PLURALS: tuple[str, ...] = (
    "incidents",
    "tickets",
    "cases",
    "complaints",
    "reports",
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
    "threshold",
    "minimum stock",
    "min stock",
    "below minimum",
)

INVENTORY_WRITE_SIGNALS: tuple[str, ...] = (
    "restock",
    "inbound",
    "outbound",
    "adjust stock",
    "adjust inventory",
    "create product",
    "add stock",
    "update stock",
    "delete product",
)

PROCEDURE_PHRASES: tuple[str, ...] = (
    "how do i",
    "how do you",
    "how can i",
    "how does one",
    "how should i",
    "how to",
    "what should we",
    "what is the procedure",
    "what's the procedure",
    "steps to",
    "guide to",
    "walk me through",
)

SUMMARY_SIGNALS: tuple[str, ...] = (
    "how many incident",
    "how many open incident",
    "incident summary",
    "incident count",
    "total incident",
    "breakdown by",
    "by status",
    "by category",
    "by branch",
    "by origin",
    "count of open",
    "count of incident",
)

_PROCEDURE_PHRASING_RE = re.compile(
    r"\bhow (?:do i|do you|does one|can i|to|should i)\b",
    re.IGNORECASE,
)
_INSTRUCTIVE_CREATE_RE = re.compile(
    r"\bhow (?:do i|do you|does one|can i|to|should i)\b"
    r".*\b(create|open|log|file|report)\s+(?:an?\s+)?(incident|ticket|case)\b",
    re.IGNORECASE,
)
_SUMMARY_RE = re.compile(r"\bhow many\b.*\bincidents?\b", re.IGNORECASE)
_LIST_INCIDENT_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bshow(?:\s+me)?\s+(?:all\s+)?incidents?\b", re.IGNORECASE),
    re.compile(r"\blist(?:\s+all|\s+open)?\s+incidents?\b", re.IGNORECASE),
    re.compile(r"\b(?:all|every)\s+incidents?\b", re.IGNORECASE),
    re.compile(r"\bget\s+(?:all\s+)?incidents?\b", re.IGNORECASE),
)

GENERIC_ISSUE_WORDS: frozenset[str] = frozenset({"issue", "problem", "help", "error"})

_INCIDENT_ID_RE = re.compile(r"\bincident\s+#?(\d+)\b", re.IGNORECASE)
_HASH_ID_RE = re.compile(r"#(\d+)\b")
_CREATE_RE = re.compile(
    r"\b(create|open|log|file|report)\s+(an?\s+)?(incident|ticket|case)\b",
    re.IGNORECASE,
)
_UPDATE_RE = re.compile(
    r"\b(mark|update|set|change|resolve|close|discard)\s+"
    r"(?:incident\s+)?#?(\d+)\b",
    re.IGNORECASE,
)
_UPDATE_TO_RE = re.compile(
    r"\b(?:incident\s+)?#?(\d+)\s+(?:to|as)\s+"
    r"(open|in[\s_]?progress|resolved|discarded|closed)\b",
    re.IGNORECASE,
)

CATEGORY_LABELS: dict[str, str] = {
    value: value.replace("_", " ") for value in CATEGORY_VALUES
}


@dataclass(frozen=True)
class ClassifyResult:
    intent: Intent
    incident_id: int | None = None
    incident_filters: dict[str, str] = field(default_factory=dict)
    incident_action: IncidentAction = "list"
    write_action: WriteAction | None = None
    write_payload: dict[str, str] | None = None
    write_status: str | None = None
    matched: list[str] = field(default_factory=list)


def has_procedure_phrasing(text: str) -> bool:
    """True when the question uses instructional / policy phrasing (P24-OPT-F)."""
    lower = (text or "").lower()
    if _PROCEDURE_PHRASING_RE.search(lower):
        return True
    if any(_contains_phrase(lower, phrase) for phrase in PROCEDURE_PHRASES):
        return True
    return any(
        _contains_phrase(lower, signal)
        for signal in ("procedure", "procedures", "policy", "policies")
    )


def _is_instructive_incident_question(text: str) -> bool:
    """How-to about creating/logging incidents — not an imperative write."""
    if not _INSTRUCTIVE_CREATE_RE.search(text):
        return False
    lower = text.lower()
    scratch: list[str] = []
    return _extract_branch(lower, scratch) is None


def classify_question(question: str) -> ClassifyResult:
    """Pure rule-based intent classification — no HTTP, RAG, or LLM (P2-L22)."""
    text = (question or "").strip()
    matched: list[str] = []

    if _is_procedure_question(text, matched):
        return ClassifyResult(intent="rag", matched=matched + ["intent:rag"])

    if _has_inventory_write_signals(text, matched):
        matched.append("intent:inventory_write")
        return ClassifyResult(intent="inventory_write", matched=matched)

    write_result = _detect_write_intent(text, matched)
    if write_result is not None:
        return write_result

    from agent.memory.correction_intent import looks_like_memory_correction

    if looks_like_memory_correction(text):
        from agent.memory.proposal import extract_continued_question, matches_approve_with_memory_intent

        continued = (
            extract_continued_question(text)
            if matches_approve_with_memory_intent(text)
            else None
        )
        if continued:
            matched.append("approve_and_continue")
            return classify_question(continued)
        matched.append("memory_correction")
        matched.append("intent:rag")
        return ClassifyResult(intent="rag", matched=matched)

    if _looks_like_operational_policy_question(text) and not _has_core_incident_signals(
        text, matched, relaxed_hash=False
    ):
        matched.append("operational_policy")
        matched.append("intent:rag")
        return ClassifyResult(intent="rag", matched=matched)

    has_incident = _has_incident_signals(text, matched)
    has_kb = _has_kb_signals(text, matched)
    has_inventory = _has_inventory_signals(text, matched)

    if not has_inventory:
        from agent.tools.inventory import extract_inventory_hints, has_actionable_inventory_hints

        inv_hints = extract_inventory_hints(text)
        if has_actionable_inventory_hints(inv_hints):
            has_inventory = True
            matched.append("inventory:hints")

    incident_id = _extract_incident_id(text, has_incident)
    incident_filters = _extract_incident_filters(text, matched, incident_id)
    incident_action = _detect_incident_action(text, matched, incident_id)

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
        incident_action=incident_action,
        matched=matched,
    )


def looks_like_live_ops_question(question: str) -> bool:
    """True when the question appears to ask for live incidents or inventory data."""
    text = (question or "").strip()
    if not text:
        return False
    scratch: list[str] = []
    if _has_incident_signals(text, scratch, relaxed_hash=False):
        return True
    if _has_inventory_signals(text, scratch):
        return True
    from agent.tools.inventory import extract_inventory_hints, has_actionable_inventory_hints

    if has_actionable_inventory_hints(extract_inventory_hints(text)):
        return True
    return False


def has_brasaland_domain_signals(question: str) -> bool:
    """Tier 0 allowlist — Brasaland ops, KB, procedure, or write phrasing (P25-L11b)."""
    text = (question or "").strip()
    if not text:
        return False

    lower = text.lower()
    if "brasaland" in lower or "brasa points" in lower:
        return True

    matched: list[str] = []
    if _has_kb_signals(text, matched):
        return True
    if looks_like_live_ops_question(text):
        return True
    if has_procedure_phrasing(text):
        return True
    if _has_inventory_write_signals(text, matched):
        return True
    if _CREATE_RE.search(text) or _UPDATE_RE.search(text) or _UPDATE_TO_RE.search(text):
        return True
    return False


def _contains_phrase(text: str, phrase: str) -> bool:
    if " " in phrase:
        return phrase in text
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def _is_procedure_question(text: str, matched: list[str]) -> bool:
    lower = text.lower()

    if _is_instructive_incident_question(text):
        matched.append("procedure_guard:instructive_incident")
        return True

    if _PROCEDURE_PHRASING_RE.search(lower):
        has_live_data = (
            _has_incident_signals(lower, matched, relaxed_hash=False)
            or _has_inventory_signals(lower, matched)
            or _UPDATE_RE.search(text) is not None
            or _UPDATE_TO_RE.search(text) is not None
        )
        if not has_live_data:
            matched.append("procedure_guard")
            return True

    has_procedure = any(_contains_phrase(lower, phrase) for phrase in PROCEDURE_PHRASES)
    if not has_procedure:
        for signal in ("procedure", "procedures", "policy", "policies"):
            if _contains_phrase(lower, signal):
                has_procedure = True
                matched.append(f"procedure:{signal}")
                break
    if not has_procedure:
        return False

    has_live_data = (
        _has_incident_signals(lower, matched, relaxed_hash=False)
        or _has_inventory_signals(lower, matched)
        or _UPDATE_RE.search(text) is not None
        or _UPDATE_TO_RE.search(text) is not None
    )
    if has_live_data:
        return False

    matched.append("procedure_guard")
    return True


def _detect_write_intent(text: str, matched: list[str]) -> ClassifyResult | None:
    lower = text.lower()

    update_to = _UPDATE_TO_RE.search(text)
    if update_to:
        incident_id = int(update_to.group(1))
        status_raw = update_to.group(2).replace(" ", "_").lower()
        status = "resolved" if status_raw == "closed" else status_raw
        if status in STATUS_VALUES:
            matched.append("write:update_status")
            matched.append(f"write_status:{status}")
            matched.append("intent:incident_write")
            return ClassifyResult(
                intent="incident_write",
                incident_id=incident_id,
                write_action="update_status",
                write_status=status,
                matched=matched,
            )

    update_match = _UPDATE_RE.search(text)
    if update_match:
        incident_id = int(update_match.group(2))
        status = _extract_status_from_text(lower, matched)
        if status:
            matched.append("write:update_status")
            matched.append("intent:incident_write")
            return ClassifyResult(
                intent="incident_write",
                incident_id=incident_id,
                write_action="update_status",
                write_status=status,
                matched=matched,
            )

    if _CREATE_RE.search(text):
        if _is_instructive_incident_question(text):
            return None
        payload = _extract_create_payload(text, matched)
        if payload:
            matched.append("write:create")
            matched.append("intent:incident_write")
            return ClassifyResult(
                intent="incident_write",
                write_action="create",
                write_payload=payload,
                matched=matched,
            )

    return None


def _extract_status_from_text(lower: str, matched: list[str]) -> str | None:
    for status_phrase, status_value in STATUS_PHRASES:
        if _contains_phrase(lower, status_phrase):
            matched.append(f"write_status:{status_value}")
            return status_value
    if _contains_phrase(lower, "close") or _contains_phrase(lower, "resolved"):
        matched.append("write_status:resolved")
        return "resolved"
    if _contains_phrase(lower, "discard"):
        matched.append("write_status:discarded")
        return "discarded"
    return None


def _extract_create_payload(text: str, matched: list[str]) -> dict[str, str] | None:
    lower = text.lower()
    branch = _extract_branch(lower, matched)
    if not branch:
        return None

    category = _extract_category(lower, matched) or "other"
    origin = _extract_origin(lower, matched) or "internal"

    detail = _CREATE_RE.sub("", text, count=1).strip(" .:-")
    detail = re.sub(r"^\s*for\s+", "", detail, flags=re.IGNORECASE).strip(" .:-")

    branch_label = BRANCH_LABELS.get(branch, branch.replace("_", " "))
    for pattern in (branch_label, branch.replace("_", " "), branch):
        detail = re.sub(
            rf"\bat\s+{re.escape(pattern)}\b",
            "",
            detail,
            flags=re.IGNORECASE,
        ).strip(" .:-,")

    if ":" in detail:
        title_part, desc_part = detail.split(":", 1)
        title = title_part.strip()
        description = desc_part.strip() or title
    else:
        title = detail.strip()
        description = title

    if not title:
        title = "Incident reported via Support Agent"
    if not description:
        description = title

    if title and title[0].islower():
        title = title[0].upper() + title[1:]

    matched.append(f"write_branch:{branch}")
    matched.append(f"write_category:{category}")
    matched.append(f"write_origin:{origin}")

    return {
        "title": title[:120].strip(),
        "description": description.strip(),
        "category": category,
        "origin": origin,
        "branch": branch,
    }


def _extract_branch(lower: str, matched: list[str]) -> str | None:
    for branch in BRANCH_VALUES:
        pattern = branch.replace("_", " ")
        if _contains_phrase(lower, pattern) or _contains_phrase(lower, branch):
            matched.append(f"branch:{branch}")
            return branch
    for key, label in BRANCH_LABELS.items():
        if _contains_phrase(lower, label.lower()):
            matched.append(f"branch_label:{label}")
            return key
    return None


def _extract_category(lower: str, matched: list[str]) -> str | None:
    for value in CATEGORY_VALUES:
        label = value.replace("_", " ")
        if _contains_phrase(lower, label) or _contains_phrase(lower, value):
            matched.append(f"category:{value}")
            return value
    for label, value in LEGACY_CATEGORY_MAP.items():
        if _contains_phrase(lower, label):
            matched.append(f"category:{value}")
            return value
    return None


def _extract_origin(lower: str, matched: list[str]) -> str | None:
    for origin in ORIGIN_VALUES:
        if _contains_phrase(lower, origin):
            matched.append(f"origin:{origin}")
            return origin
    return None


def _detect_incident_action(
    text: str,
    matched: list[str],
    incident_id: int | None,
) -> IncidentAction:
    if incident_id is not None:
        return "get"
    lower = text.lower()
    if _SUMMARY_RE.search(text):
        matched.append("action:summary")
        return "summary"
    for signal in SUMMARY_SIGNALS:
        if signal in lower:
            matched.append(f"action:summary")
            return "summary"
    return "list"


def _has_core_incident_signals(
    text: str,
    matched: list[str],
    *,
    relaxed_hash: bool = True,
) -> bool:
    """Incident list/get/summary phrasing — not branch names alone."""
    lower = text.lower()

    if _has_list_incident_phrasing(lower, matched):
        return True

    for noun in INCIDENT_NOUNS:
        if _contains_phrase(lower, noun):
            matched.append(noun)
            return True

    for plural in INCIDENT_NOUN_PLURALS:
        if _contains_phrase(lower, plural):
            matched.append(plural)
            return True

    if _INCIDENT_ID_RE.search(text):
        matched.append("incident_id_pattern")
        return True

    if relaxed_hash and _HASH_ID_RE.search(text):
        matched.append("hash_id_relaxed")
        return True

    if _HASH_ID_RE.search(text) and any(_contains_phrase(lower, n) for n in INCIDENT_NOUNS):
        matched.append("incident_id_pattern")
        return True

    for signal in SUMMARY_SIGNALS:
        if signal in lower:
            matched.append(f"summary:{signal}")
            return True

    return False


_OPERATIONAL_POLICY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bwhen\b.+\b(?:deliver\w*|delivery|supplier|vegetable|meat|produce)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:deliver\w*|delivery|supplier)\b.+\b(?:when|day|schedule|arrive)\b",
        re.I,
    ),
    re.compile(r"\bwhat day\b.+\b(?:deliver\w*|delivery|supplier)\b", re.I),
    re.compile(r"\b(?:hours?|open|clos\w*)\b.+\b(?:at|for)\s+[A-Za-z]", re.I),
)


def _looks_like_operational_policy_question(text: str) -> bool:
    """Supplier delivery / hours lookups — RAG + memory, not live incidents."""
    stripped = (text or "").strip()
    if not stripped:
        return False
    return any(pattern.search(stripped) for pattern in _OPERATIONAL_POLICY_PATTERNS)


def _has_incident_signals(
    text: str,
    matched: list[str],
    *,
    relaxed_hash: bool = True,
) -> bool:
    lower = text.lower()

    if _has_core_incident_signals(text, matched, relaxed_hash=relaxed_hash):
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


def _has_inventory_write_signals(text: str, matched: list[str]) -> bool:
    lower = text.lower()
    for signal in sorted(INVENTORY_WRITE_SIGNALS, key=len, reverse=True):
        if _contains_phrase(lower, signal):
            matched.append(f"inventory_write:{signal}")
            return True
    return False


def _has_inventory_signals(text: str, matched: list[str]) -> bool:
    lower = text.lower()
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

    origin = _extract_origin(lower, matched)
    if origin:
        filters["origin"] = origin

    branch = _extract_branch(lower, matched)
    if branch:
        filters["branch"] = branch

    category = _extract_category(lower, matched)
    if category:
        filters["category"] = category

    if "status" not in filters and not _wants_unfiltered_incident_list(lower):
        filters["status"] = "open"
        matched.append("filter_status_default:open")

    return filters


def _has_list_incident_phrasing(lower: str, matched: list[str]) -> bool:
    for pattern in _LIST_INCIDENT_RES:
        if pattern.search(lower):
            matched.append("list_incident_phrase")
            return True
    return False


def _wants_unfiltered_incident_list(lower: str) -> bool:
    """User asked for all statuses — skip default open filter."""
    if re.search(r"\b(?:all|every)\s+incidents?\b", lower):
        return True
    if re.search(r"\bshow(?:\s+me)?\s+all\s+incidents?\b", lower):
        return True
    if re.search(r"\blist\s+all\s+incidents?\b", lower):
        return True
    if re.search(r"\bany\s+status\b", lower):
        return True
    return False
