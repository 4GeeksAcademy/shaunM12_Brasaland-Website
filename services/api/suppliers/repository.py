"""TinyDB persistence layer for suppliers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .constants import SUPPLIERS_SEED
from .models import SupplierCreate, SupplierResponse
from database import get_suppliers_table


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_response(record: dict[str, Any]) -> SupplierResponse:
    return SupplierResponse.model_validate(record)


def _supplier_key(record: dict[str, Any]) -> tuple[str, str]:
    return (record["name"].strip().lower(), record["country"])


def seed_suppliers() -> tuple[int, int]:
    """Insert seed suppliers, skipping duplicates by name + country."""
    table = get_suppliers_table()
    existing_keys = {_supplier_key(row) for row in table.all()}
    added = 0
    skipped = 0
    timestamp = _utc_now_iso()

    for entry in SUPPLIERS_SEED:
        key = _supplier_key(entry)
        if key in existing_keys:
            skipped += 1
            continue

        payload = {
            **entry,
            "rate_updated_at": timestamp,
        }
        doc_id = table.insert(payload)
        table.update({"id": doc_id}, doc_ids=[doc_id])
        existing_keys.add(key)
        added += 1

    return added, skipped


def create_supplier(payload: SupplierCreate) -> SupplierResponse:
    table = get_suppliers_table()
    timestamp = _utc_now_iso()
    data = payload.model_dump(mode="json")
    data["rate_updated_at"] = timestamp
    doc_id = table.insert(data)
    table.update({"id": doc_id}, doc_ids=[doc_id])
    stored = table.get(doc_id=doc_id)
    if stored is None:
        raise RuntimeError("Failed to persist supplier")
    return _to_response(stored)


def get_supplier(supplier_id: int) -> SupplierResponse | None:
    record = get_suppliers_table().get(doc_id=supplier_id)
    if record is None:
        return None
    return _to_response(record)


def list_suppliers(
    country: str | None = None,
    category: str | None = None,
) -> list[SupplierResponse]:
    records = get_suppliers_table().all()

    if country:
        records = [row for row in records if row.get("country") == country]

    if category:
        records = [
            row
            for row in records
            if category in row.get("categories", [])
        ]

    records.sort(key=lambda row: (row.get("country", ""), row.get("name", "")))
    return [_to_response(row) for row in records]


def update_supplier_rate(
    supplier_id: int,
    rate_per_unit: float,
) -> SupplierResponse | None:
    table = get_suppliers_table()
    record = table.get(doc_id=supplier_id)
    if record is None:
        return None

    timestamp = _utc_now_iso()
    table.update(
        {"rate_per_unit": rate_per_unit, "rate_updated_at": timestamp},
        doc_ids=[supplier_id],
    )
    updated = table.get(doc_id=supplier_id)
    return _to_response(updated) if updated else None


def update_supplier_status(
    supplier_id: int,
    status: str,
) -> SupplierResponse | None:
    table = get_suppliers_table()
    record = table.get(doc_id=supplier_id)
    if record is None:
        return None

    table.update({"status": status}, doc_ids=[supplier_id])
    updated = table.get(doc_id=supplier_id)
    return _to_response(updated) if updated else None


def update_supplier_notes(
    supplier_id: int,
    notes: str | None,
) -> SupplierResponse | None:
    table = get_suppliers_table()
    record = table.get(doc_id=supplier_id)
    if record is None:
        return None

    table.update({"notes": notes}, doc_ids=[supplier_id])
    updated = table.get(doc_id=supplier_id)
    return _to_response(updated) if updated else None


def delete_supplier(supplier_id: int) -> bool:
    table = get_suppliers_table()
    record = table.get(doc_id=supplier_id)
    if record is None:
        return False
    table.remove(doc_ids=[supplier_id])
    return True
