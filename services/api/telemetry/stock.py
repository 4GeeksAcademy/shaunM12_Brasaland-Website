"""Stock threshold crossing detection and emission."""

from __future__ import annotations

from sqlmodel import Session

from .context import EmitContext
from .dedupe import record_threshold_emission, should_emit_threshold_crossing
from .emit import emit_event


def maybe_emit_stock_threshold_triggered(
    session: Session,
    *,
    product_id: int,
    product_category: str,
    location_id: int,
    unit: str,
    stock_before: float,
    stock_after: float,
    min_stock_threshold: float,
    triggering_order_type: str,
    triggering_order_id: int,
    quantity: float | None = None,
    ctx: EmitContext | None = None,
) -> None:
    if not should_emit_threshold_crossing(
        ingredient_id=product_id,
        location_id=location_id,
        stock_before=stock_before,
        stock_after=stock_after,
        threshold=min_stock_threshold,
    ):
        return

    properties: dict = {
        "product_id": product_id,
        "product_category": product_category,
        "location_id": location_id,
        "current_stock": stock_after,
        "min_stock_threshold": min_stock_threshold,
        "unit": unit,
        "triggering_order_type": triggering_order_type,
        "triggering_order_id": triggering_order_id,
    }
    if quantity is not None:
        properties["quantity"] = quantity

    emit_event(
        "stock_threshold_triggered",
        properties,
        ctx=ctx,
        session=session,
    )
    record_threshold_emission(ingredient_id=product_id, location_id=location_id)
