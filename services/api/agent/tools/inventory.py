"""Inventory lookup tool — HTTP to bare FastAPI ``/inventory/products`` (P2-L9, P24-OPT)."""

from __future__ import annotations

import os
import re
from typing import Any

from packages.shared.restaurant_locations import format_location_label, resolve_location_hint

from .http import fetch_json

INVENTORY_SOURCE = "inventory_api"
NAME_MATCH_ROW_CAP = 5

_SKU_RE = re.compile(r"\bSKU\s+([A-Za-z0-9-]+)\b", re.IGNORECASE)
_PRODUCT_ID_RE = re.compile(r"\bproduct\s+#?(\d+)\b", re.IGNORECASE)
_LOCATION_ID_RE = re.compile(r"\blocation(?:\s+id)?\s+#?(\d+)\b", re.IGNORECASE)
_LOCATION_HASH_RE = re.compile(r"\bid#(\d+)\b", re.IGNORECASE)
_CATALOG_SKU_RE = re.compile(r"\b([A-Z]{2,}-[A-Z0-9-]+)\b")
_NAME_FOR_RE = re.compile(
    r"\b(?:stock|inventory)\s+(?:for|of)\s+([A-Za-z0-9][A-Za-z0-9\s'-]{2,60})",
    re.IGNORECASE,
)
_NAME_HOW_MUCH_RE = re.compile(
    r"\bhow much\s+([A-Za-z0-9][A-Za-z0-9'-]{2,40})(?:\s+do we have|\s+at\b|\s*\?|$)",
    re.IGNORECASE,
)
_NAME_STOCK_SUFFIX_RE = re.compile(
    r"\b([A-Za-z0-9][A-Za-z0-9\s'-]{2,40})\s+stock\b",
    re.IGNORECASE,
)
_DO_WE_HAVE_RE = re.compile(
    r"\bdo we have\s+(?:any\s+)?([A-Za-z0-9][A-Za-z0-9\s'-]{2,40})(?:\s+at\b|\s*\?|$)",
    re.IGNORECASE,
)
_QUOTED_NAME_RE = re.compile(r'"([^"]{2,60})"|\'([^\']{2,60})\'')


def default_location_id() -> int:
    raw = os.getenv("AGENT_DEFAULT_LOCATION_ID", "1").strip()
    try:
        value = int(raw)
    except ValueError:
        return 1
    return value if 1 <= value <= 14 else 1


def extract_inventory_hints(question: str) -> dict[str, Any]:
    """Parse SKU, product_id, location_id, and name hints from the user question."""
    text = (question or "").strip()
    hints: dict[str, Any] = {}

    sku_match = _SKU_RE.search(text)
    if sku_match:
        hints["sku"] = sku_match.group(1).upper()
    else:
        catalog_match = _CATALOG_SKU_RE.search(text)
        if catalog_match:
            hints["sku"] = catalog_match.group(1).upper()

    product_match = _PRODUCT_ID_RE.search(text)
    if product_match:
        hints["product_id"] = int(product_match.group(1))

    location_match = _LOCATION_ID_RE.search(text) or _LOCATION_HASH_RE.search(text)
    if location_match:
        hints["location_id"] = int(location_match.group(1))
    else:
        location_hint = resolve_location_hint(text)
        if location_hint is not None:
            hints["location_id"] = location_hint

    name_match = _NAME_FOR_RE.search(text)
    if name_match:
        name = name_match.group(1).strip(" .,?")
        if name and "sku" not in name.lower():
            hints["name"] = _strip_location_from_name(name, hints)

    if "name" not in hints:
        extracted = _extract_name_from_patterns(text, hints)
        if extracted:
            hints["name"] = extracted

    return hints


def _strip_location_from_name(name: str, hints: dict[str, Any]) -> str:
    cleaned = re.sub(r"\s+at\s+.+$", "", name, flags=re.IGNORECASE).strip(" .,?")
    return cleaned or name


def _extract_name_from_patterns(text: str, hints: dict[str, Any]) -> str | None:
    for pattern in (_NAME_HOW_MUCH_RE, _DO_WE_HAVE_RE, _NAME_STOCK_SUFFIX_RE):
        match = pattern.search(text)
        if not match:
            continue
        name = match.group(1).strip(" .,?")
        name = _strip_location_from_name(name, hints)
        if name and len(name) >= 2 and "sku" not in name.lower():
            return name

    quoted = _QUOTED_NAME_RE.search(text)
    if quoted:
        name = (quoted.group(1) or quoted.group(2) or "").strip()
        if name and len(name) >= 2:
            return name
    return None


def has_actionable_inventory_hints(hints: dict[str, Any]) -> bool:
    return any(key in hints for key in ("sku", "product_id", "name"))


def _normalize_row(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "sku": raw.get("sku"),
        "unit": raw.get("unit"),
        "category": raw.get("category"),
        "country": raw.get("country"),
        "current_stock": raw.get("current_stock"),
        "min_stock_threshold": raw.get("min_stock_threshold"),
        "location_id": raw.get("location_id"),
    }


def _failure_envelope(
    *,
    http_status: int,
    reason: str,
    error: str | None = None,
    product_id: int | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "source": INVENTORY_SOURCE,
        "ok": False,
        "http_status": http_status,
        "rows": [],
        "error": error or reason,
        "reason": reason,
    }
    if product_id is not None:
        envelope["product_id"] = product_id
    if filters:
        envelope["filters"] = filters
    return envelope


def _sku_matches(candidate: str, query: str) -> bool:
    candidate_norm = candidate.upper()
    query_norm = query.upper()
    return candidate_norm == query_norm or query_norm in candidate_norm


def _name_matches(candidate: str, query: str) -> bool:
    return query.lower() in (candidate or "").lower()


def lookup_inventory_stock(
    *,
    question: str,
    auth_header: str | None,
) -> dict[str, Any]:
    """Call inventory API and return a P2-L36 envelope."""
    hints = extract_inventory_hints(question)
    filters: dict[str, Any] = dict(hints)

    if not has_actionable_inventory_hints(hints):
        return _failure_envelope(
            http_status=0,
            reason="needs_clarification",
            filters=filters,
        )

    headers: dict[str, str] = {}
    if auth_header:
        headers["Authorization"] = auth_header

    product_id = hints.get("product_id")
    location_id = hints.get("location_id")
    sku_query = hints.get("sku")
    name_query = hints.get("name")

    if location_id is None:
        location_id = default_location_id()
        filters["location_id"] = location_id

    if product_id is not None:
        params: dict[str, Any] = {"location_id": location_id}
        status, body, transport_reason = fetch_json(
            "GET",
            f"/inventory/products/{product_id}",
            params=params,
            headers=headers,
        )
        if transport_reason == "timeout":
            return _failure_envelope(
                http_status=0,
                reason="timeout",
                product_id=product_id,
                filters=filters,
            )
        if transport_reason is not None:
            return _failure_envelope(
                http_status=status,
                reason="http_error",
                product_id=product_id,
                filters=filters,
            )
        if status == 404:
            return _failure_envelope(
                http_status=404,
                reason="not_found",
                product_id=product_id,
                filters=filters,
            )
        if status >= 400:
            return _failure_envelope(
                http_status=status,
                reason=f"http_{status}",
                product_id=product_id,
                filters=filters,
            )
        if not isinstance(body, dict):
            return _failure_envelope(
                http_status=status,
                reason="invalid_response",
                product_id=product_id,
                filters=filters,
            )
        row = _normalize_row(body)
        row["location_id"] = location_id
        return {
            "source": INVENTORY_SOURCE,
            "ok": True,
            "http_status": status,
            "product_id": product_id,
            "filters": filters,
            "rows": [row],
            "error": None,
            "reason": None,
        }

    status, body, transport_reason = fetch_json(
        "GET",
        "/inventory/products",
        params={"location_id": location_id},
        headers=headers,
    )
    if transport_reason == "timeout":
        return _failure_envelope(http_status=0, reason="timeout", filters=filters)
    if transport_reason is not None:
        return _failure_envelope(
            http_status=status,
            reason="http_error",
            filters=filters,
        )
    if status >= 400:
        return _failure_envelope(
            http_status=status,
            reason=f"http_{status}",
            filters=filters,
        )
    if not isinstance(body, list):
        return _failure_envelope(
            http_status=status,
            reason="invalid_response",
            filters=filters,
        )

    rows = [_normalize_row(item) for item in body if isinstance(item, dict)]
    if sku_query:
        rows = [row for row in rows if _sku_matches(str(row.get("sku") or ""), sku_query)]
    elif name_query:
        rows = [
            row for row in rows if _name_matches(str(row.get("name") or ""), name_query)
        ]

    for row in rows:
        row["location_id"] = location_id

    if not rows:
        return {
            "source": INVENTORY_SOURCE,
            "ok": True,
            "http_status": status,
            "filters": filters,
            "rows": [],
            "error": None,
            "reason": "empty",
        }

    truncated = False
    if name_query and len(rows) > NAME_MATCH_ROW_CAP:
        rows = rows[:NAME_MATCH_ROW_CAP]
        truncated = True

    envelope: dict[str, Any] = {
        "source": INVENTORY_SOURCE,
        "ok": True,
        "http_status": status,
        "filters": filters,
        "rows": rows,
        "error": None,
        "reason": None,
    }
    if truncated:
        envelope["truncated"] = True
        envelope["truncated_note"] = (
            f"Showing first {NAME_MATCH_ROW_CAP} name matches; refine the product name or use a SKU."
        )
    return envelope
