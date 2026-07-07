"""Stock threshold crossing detection and emission."""

from __future__ import annotations

from sqlmodel import Session

from .context import EmitContext
from .dedupe import record_threshold_emission, should_emit_threshold_crossing
from .emit import emit_event


def maybe_emit_stock_threshold_triggered(
    session: Session,
    *,
    ingredient_id: int,
    location_id: int,
    stock_before: float,
    stock_after: float,
    min_stock_threshold: float,
    triggering_order_type: str,
    triggering_order_id: int,
    ctx: EmitContext | None = None,
) -> None:
    if not should_emit_threshold_crossing(
        ingredient_id=ingredient_id,
        location_id=location_id,
        stock_before=stock_before,
        stock_after=stock_after,
        threshold=min_stock_threshold,
    ):
        return

    emit_event(
        "stock_threshold_triggered",
        {
            "ingredient_id": ingredient_id,
            "location_id": location_id,
            "current_stock": stock_after,
            "min_stock_threshold": min_stock_threshold,
            "triggering_order_type": triggering_order_type,
            "triggering_order_id": triggering_order_id,
        },
        ctx=ctx,
        session=session,
    )
    record_threshold_emission(ingredient_id=ingredient_id, location_id=location_id)
