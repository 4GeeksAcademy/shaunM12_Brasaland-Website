"""``query_inventory`` MCP tool — read-only (P24-L6, P24-L15)."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from .. import errors
from ..scopes import require_scope
from ..upstream import map_upstream_failure, request_json

InventoryAction = Literal["query"]

_WRITE_KEYWORDS = frozenset(
    {
        "create",
        "update",
        "delete",
        "patch",
        "inbound",
        "outbound",
        "adjust",
        "restock",
        "write",
        "mutate",
    }
)


class InventoryQueryInput(BaseModel):
    action: InventoryAction = Field(
        default="query",
        description="Must be 'query'. Write actions are explicitly rejected.",
    )
    product_id: int | None = Field(default=None, description="Filter by product id.")
    sku: str | None = Field(default=None, description="Filter by SKU (partial match).")
    location_id: int | None = Field(
        default=None,
        ge=1,
        le=14,
        description="Location id 1–14 for stock context.",
    )
    name: str | None = Field(default=None, description="Partial product name match.")


def _write_signal_detected(raw: dict[str, Any]) -> bool:
    action = str(raw.get("action", "query")).strip().lower()
    if action != "query":
        return True
    for key, value in raw.items():
        if key == "action":
            continue
        if isinstance(value, str) and value.strip().lower() in _WRITE_KEYWORDS:
            return True
        if re.search(
            r"\b(" + "|".join(re.escape(word) for word in sorted(_WRITE_KEYWORDS)) + r")\b",
            str(value).lower(),
        ):
            return True
    return False


def inventory_write_forbidden_message() -> str:
    return (
        "Inventory writes are forbidden via MCP. This tool is read-only. "
        "Use Brasaland backoffice order flows for inbound/outbound stock changes."
    )


def query_inventory(
    action: InventoryAction = "query",
    product_id: int | None = None,
    sku: str | None = None,
    location_id: int | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Read-only inventory queries (products, stock, thresholds). Writes are rejected."""
    raw = {
        "action": action,
        "product_id": product_id,
        "sku": sku,
        "location_id": location_id,
        "name": name,
    }
    if _write_signal_detected(raw):
        return errors.error_payload(
            errors.INVENTORY_WRITE_FORBIDDEN,
            inventory_write_forbidden_message(),
        )

    scope_error = require_scope("inventory:read")
    if scope_error:
        return scope_error

    if product_id is not None:
        return _fetch_product(product_id, location_id)

    status_code, body, transport_error = request_json(
        "GET",
        "/inventory/products",
        params={"location_id": str(location_id)} if location_id is not None else None,
    )
    if transport_error or status_code >= 400:
        return map_upstream_failure(
            status=status_code,
            body=body,
            transport_error=transport_error,
            action="query",
        )

    rows = body if isinstance(body, list) else []
    filtered = _filter_rows(rows, sku=sku, name=name)
    return {"ok": True, "action": "query", "count": len(filtered), "data": filtered}


def _fetch_product(product_id: int, location_id: int | None) -> dict[str, Any]:
    params = {"location_id": str(location_id)} if location_id is not None else None
    status_code, body, transport_error = request_json(
        "GET",
        f"/inventory/products/{product_id}",
        params=params,
    )
    if transport_error or status_code >= 400:
        return map_upstream_failure(
            status=status_code,
            body=body,
            transport_error=transport_error,
            action="query",
        )
    return {"ok": True, "action": "query", "count": 1, "data": [body]}


def _filter_rows(
    rows: list[Any],
    *,
    sku: str | None,
    name: str | None,
) -> list[Any]:
    if not sku and not name:
        return rows
    result: list[Any] = []
    sku_norm = sku.upper().strip() if sku else None
    name_norm = name.strip().lower() if name else None
    for row in rows:
        if not isinstance(row, dict):
            continue
        if sku_norm:
            candidate = str(row.get("sku", "")).upper()
            if sku_norm not in candidate:
                continue
        if name_norm:
            candidate = str(row.get("name", "")).lower()
            if name_norm not in candidate:
                continue
        result.append(row)
    return result
