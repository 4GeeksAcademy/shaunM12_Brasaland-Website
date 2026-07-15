"""Ingredient price variance detection for course-floor telemetry."""

from __future__ import annotations

from sqlmodel import Session, select

from inventory.models import IngredientEntry

from .constants import PRICE_VARIANCE_THRESHOLD_PCT
from .context import EmitContext
from .emit import emit_event


def last_unit_cost(
    session: Session,
    *,
    product_id: int,
    supplier_id: int,
    exclude_entry_id: int | None = None,
) -> float | None:
    """Most recent persisted unit cost for product+supplier (same currency history)."""
    query = (
        select(IngredientEntry)
        .where(
            IngredientEntry.ingredient_id == product_id,
            IngredientEntry.supplier_id == supplier_id,
            IngredientEntry.unit_cost != None,  # noqa: E711
        )
        .order_by(IngredientEntry.created_at.desc())  # type: ignore[attr-defined]
    )
    rows = session.exec(query).all()
    for row in rows:
        if exclude_entry_id is not None and row.id == exclude_entry_id:
            continue
        if row.unit_cost is not None:
            return float(row.unit_cost)
    return None


def maybe_emit_ingredient_price_variance(
    session: Session,
    *,
    inbound_order_id: int,
    product_id: int,
    product_category: str,
    supplier_id: int,
    location_id: int,
    quantity: float,
    unit: str,
    new_unit_cost: float | None,
    ctx: EmitContext | None = None,
    threshold_pct: float = PRICE_VARIANCE_THRESHOLD_PCT,
) -> None:
    if new_unit_cost is None:
        return
    previous = last_unit_cost(
        session,
        product_id=product_id,
        supplier_id=supplier_id,
        exclude_entry_id=inbound_order_id,
    )
    if previous is None or previous == 0:
        return

    variance_pct = ((float(new_unit_cost) - previous) / previous) * 100.0
    if abs(variance_pct) < threshold_pct:
        return

    emit_event(
        "ingredient_price_variance_detected",
        {
            "inbound_order_id": inbound_order_id,
            "product_id": product_id,
            "product_category": product_category,
            "supplier_id": str(supplier_id),
            "location_id": location_id,
            "quantity": quantity,
            "unit": unit,
            "previous_unit_cost": previous,
            "new_unit_cost": float(new_unit_cost),
            "variance_pct": round(variance_pct, 4),
            "threshold_pct": threshold_pct,
        },
        ctx=ctx,
        session=session,
    )
