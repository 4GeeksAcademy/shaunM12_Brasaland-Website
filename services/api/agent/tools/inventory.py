"""Inventory lookup tool — HTTP to bare FastAPI ``/inventory/products`` (P2-L9, P2-L36)."""

from __future__ import annotations

import re
from typing import Any

from .http import fetch_json

INVENTORY_SOURCE = "inventory_api"

_SKU_RE = re.compile(r"\bSKU\s+([A-Za-z0-9-]+)\b", re.IGNORECASE)
_PRODUCT_ID_RE = re.compile(r"\bproduct\s+#?(\d+)\b", re.IGNORECASE)
_LOCATION_ID_RE = re.compile(r"\blocation(?:\s+id)?\s+#?(\d+)\b", re.IGNORECASE)
_CATALOG_SKU_RE = re.compile(r"\b([A-Z]{2,}-[A-Z0-9-]+)\b")


def extract_inventory_hints(question: str) -> dict[str, Any]:
    """Parse SKU, product_id, and location_id hints from the user question."""
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

    location_match = _LOCATION_ID_RE.search(text)
    if location_match:
        hints["location_id"] = int(location_match.group(1))

    return hints


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


def lookup_inventory_stock(
    *,
    question: str,
    auth_header: str | None,
) -> dict[str, Any]:
    """Call inventory API and return a P2-L36 envelope."""
    hints = extract_inventory_hints(question)
    filters: dict[str, Any] = dict(hints)
    headers: dict[str, str] = {}
    if auth_header:
        headers["Authorization"] = auth_header

    product_id = hints.get("product_id")
    location_id = hints.get("location_id")
    sku_query = hints.get("sku")

    if product_id is not None:
        params: dict[str, Any] = {}
        if location_id is not None:
            params["location_id"] = location_id
        status, body, transport_reason = fetch_json(
            "GET",
            f"/inventory/products/{product_id}",
            params=params or None,
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
        if location_id is not None:
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

    params = {}
    if location_id is not None:
        params["location_id"] = location_id

    status, body, transport_reason = fetch_json(
        "GET",
        "/inventory/products",
        params=params or None,
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

    if location_id is not None:
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

    return {
        "source": INVENTORY_SOURCE,
        "ok": True,
        "http_status": status,
        "filters": filters,
        "rows": rows,
        "error": None,
        "reason": None,
    }
