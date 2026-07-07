"""In-process dedupe for stock_threshold_triggered (24h window)."""

from __future__ import annotations

import time
from dataclasses import dataclass

DEDUPE_WINDOW_SECONDS = 86400


@dataclass
class _ThresholdState:
    last_emit_at: float


_state: dict[tuple[int, int], _ThresholdState] = {}


def clear_threshold_dedupe() -> None:
    """Reset dedupe state — for tests only."""
    _state.clear()


def note_stock_recovery(
    *,
    ingredient_id: int,
    location_id: int,
    stock_after: float,
    threshold: float,
) -> None:
    """Clear dedupe when stock rises above threshold (allows re-emit on next cross)."""
    if stock_after > threshold:
        _state.pop((ingredient_id, location_id), None)


def should_emit_threshold_crossing(
    *,
    ingredient_id: int,
    location_id: int,
    stock_before: float,
    stock_after: float,
    threshold: float,
) -> bool:
    """Edge-triggered: emit only on downward cross; dedupe within 24h."""
    note_stock_recovery(
        ingredient_id=ingredient_id,
        location_id=location_id,
        stock_after=stock_after,
        threshold=threshold,
    )
    if not (stock_before > threshold and stock_after <= threshold):
        return False

    key = (ingredient_id, location_id)
    now = time.time()
    existing = _state.get(key)
    if existing is not None and (now - existing.last_emit_at) < DEDUPE_WINDOW_SECONDS:
        return False
    return True


def record_threshold_emission(*, ingredient_id: int, location_id: int) -> None:
    _state[(ingredient_id, location_id)] = _ThresholdState(last_emit_at=time.time())
