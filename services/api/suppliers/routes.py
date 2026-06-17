"""FastAPI routes for the supplier directory."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from .models import (
    SupplierCreate,
    SupplierNotesUpdate,
    SupplierRateUpdate,
    SupplierResponse,
    SupplierStatusUpdate,
)
from .repository import (
    create_supplier,
    delete_supplier,
    get_supplier,
    list_suppliers,
    update_supplier_notes,
    update_supplier_rate,
    update_supplier_status,
)

router = APIRouter(tags=["suppliers"])


@router.post("", response_model=SupplierResponse, status_code=201)
def register_supplier(payload: SupplierCreate) -> SupplierResponse:
    return create_supplier(payload)


@router.get("", response_model=list[SupplierResponse])
def get_suppliers(
    country: str | None = Query(default=None),
    category: str | None = Query(default=None),
) -> list[SupplierResponse]:
    return list_suppliers(country=country, category=category)


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier_by_id(supplier_id: int) -> SupplierResponse:
    supplier = get_supplier(supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.patch("/{supplier_id}/rate", response_model=SupplierResponse)
def patch_supplier_rate(
    supplier_id: int,
    payload: SupplierRateUpdate,
) -> SupplierResponse:
    supplier = update_supplier_rate(supplier_id, payload.rate_per_unit)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.patch("/{supplier_id}/status", response_model=SupplierResponse)
def patch_supplier_status(
    supplier_id: int,
    payload: SupplierStatusUpdate,
) -> SupplierResponse:
    supplier = update_supplier_status(supplier_id, payload.status)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.patch("/{supplier_id}/notes", response_model=SupplierResponse)
def patch_supplier_notes(
    supplier_id: int,
    payload: SupplierNotesUpdate,
) -> SupplierResponse:
    notes = payload.notes.strip() if payload.notes else None
    supplier = update_supplier_notes(supplier_id, notes)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.delete("/{supplier_id}", status_code=204)
def remove_supplier(supplier_id: int) -> None:
    if not delete_supplier(supplier_id):
        raise HTTPException(status_code=404, detail="Supplier not found")
