"""Reusable weekly location KPI transforms (Milestone 6 Phase 2)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd

SOURCE_EVENT_TYPES = [
    "inbound_order_created",
    "stock_waste_registered",
    "stock_threshold_triggered",
    "ingredient_price_variance_detected",
    "outbound_order_created",  # context / anomaly only — not a KPI column
]

KPI_SOURCE_EVENT_TYPES = [
    "inbound_order_created",
    "stock_waste_registered",
    "stock_threshold_triggered",
    "ingredient_price_variance_detected",
]


def country_for_location(location_id: int) -> str:
    if 1 <= location_id <= 9:
        return "CO"
    if 10 <= location_id <= 14:
        return "US"
    raise ValueError(f"location_id must be 1–14, got {location_id}")


def currency_for_location(location_id: int) -> str:
    return "COP" if country_for_location(location_id) == "CO" else "USD"


def iso_week_start_utc(ts: datetime | pd.Timestamp) -> date:
    """Monday UTC of the ISO week containing ``ts``."""
    if isinstance(ts, pd.Timestamp):
        ts = ts.to_pydatetime()
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    d = ts.date()
    return d - timedelta(days=d.weekday())


def extract_window_bounds(
    *,
    lookback_weeks: int = 2,
    as_of: datetime | None = None,
) -> tuple[datetime, datetime, list[date]]:
    """Return [period_start, period_end) and ISO week_start dates to recompute."""
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)

    current_week = iso_week_start_utc(now)
    weeks = [current_week - timedelta(weeks=i) for i in range(lookback_weeks)]
    weeks = sorted(set(weeks))
    period_start = datetime.combine(weeks[0], datetime.min.time(), tzinfo=timezone.utc)
    # Exclusive end: start of next Monday after the newest week (or now+buffer).
    period_end = datetime.combine(
        current_week + timedelta(days=7),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    return period_start, period_end, weeks


def events_to_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Normalize extract rows into a flat tag-column frame."""
    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "event_type",
                "timestamp",
                "location_id",
                "country",
                "currency",
                "quantity",
                "unit_cost",
                "week_start",
            ]
        )

    frame = pd.DataFrame(rows)
    tags = pd.json_normalize(frame["tags"]) if "tags" in frame.columns else pd.DataFrame()
    if not tags.empty:
        frame = pd.concat([frame.drop(columns=["tags"]), tags], axis=1)

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["location_id"] = pd.to_numeric(frame.get("location_id"), errors="coerce")
    frame["quantity"] = pd.to_numeric(frame.get("quantity"), errors="coerce")
    frame["unit_cost"] = pd.to_numeric(frame.get("unit_cost"), errors="coerce")
    frame = frame.dropna(subset=["location_id"])
    frame["location_id"] = frame["location_id"].astype(int)
    frame = frame[
        (frame["location_id"] >= 1) & (frame["location_id"] <= 14)
    ]
    if frame.empty:
        return frame

    frame["week_start"] = frame["timestamp"].map(iso_week_start_utc)
    if "country" not in frame.columns:
        frame["country"] = frame["location_id"].map(country_for_location)
    else:
        missing = frame["country"].isna() | (frame["country"].astype(str).str.len() == 0)
        frame.loc[missing, "country"] = frame.loc[missing, "location_id"].map(
            country_for_location
        )
    if "currency" not in frame.columns:
        frame["currency"] = frame["location_id"].map(currency_for_location)
    else:
        missing = frame["currency"].isna() | (frame["currency"].astype(str).str.len() == 0)
        frame.loc[missing, "currency"] = frame.loc[missing, "location_id"].map(
            currency_for_location
        )
    return frame


def _cost_lines(frame: pd.DataFrame, event_type: str) -> tuple[pd.DataFrame, int]:
    subset = frame[frame["event_type"] == event_type].copy()
    if subset.empty:
        empty = pd.DataFrame(
            columns=[
                "location_id",
                "week_start",
                "country",
                "currency",
                "cost",
            ]
        )
        return empty, 0

    eligible = subset.dropna(subset=["quantity", "unit_cost"]).copy()
    skipped = int(len(subset) - len(eligible))
    if eligible.empty:
        empty = pd.DataFrame(
            columns=[
                "location_id",
                "week_start",
                "country",
                "currency",
                "cost",
            ]
        )
        return empty, skipped

    eligible["cost"] = eligible["quantity"].astype(float) * eligible["unit_cost"].astype(
        float
    )
    return eligible[
        ["location_id", "week_start", "country", "currency", "cost"]
    ], skipped


def transform_purchase_cost(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Sum quantity × unit_cost for inbound_order_created; skip missing cost."""
    lines, skipped = _cost_lines(frame, "inbound_order_created")
    if lines.empty:
        return (
            pd.DataFrame(
                columns=[
                    "location_id",
                    "week_start",
                    "country",
                    "currency",
                    "total_purchase_cost",
                ]
            ),
            skipped,
        )
    grouped = (
        lines.groupby(
            ["location_id", "week_start", "country", "currency"], as_index=False
        )
        .agg(total_purchase_cost=("cost", "sum"))
    )
    return grouped, skipped


def transform_waste_cost(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Sum quantity × unit_cost for stock_waste_registered; skip missing cost."""
    lines, skipped = _cost_lines(frame, "stock_waste_registered")
    if lines.empty:
        return (
            pd.DataFrame(
                columns=[
                    "location_id",
                    "week_start",
                    "country",
                    "currency",
                    "total_waste_cost",
                ]
            ),
            skipped,
        )
    grouped = (
        lines.groupby(
            ["location_id", "week_start", "country", "currency"], as_index=False
        )
        .agg(total_waste_cost=("cost", "sum"))
    )
    return grouped, skipped


def transform_waste_ratio(
    purchase: pd.DataFrame, waste: pd.DataFrame
) -> pd.DataFrame:
    """waste_ratio = total_waste_cost / total_purchase_cost (0 if no purchases)."""
    keys = ["location_id", "week_start", "country", "currency"]
    empty_cols = [*keys, "waste_ratio"]

    if purchase is None or purchase.empty:
        purchase = pd.DataFrame(columns=[*keys, "total_purchase_cost"])
    if waste is None or waste.empty:
        waste = pd.DataFrame(columns=[*keys, "total_waste_cost"])

    if purchase.empty and waste.empty:
        return pd.DataFrame(columns=empty_cols)

    if "total_purchase_cost" not in purchase.columns:
        purchase = purchase.copy()
        purchase["total_purchase_cost"] = 0.0
    if "total_waste_cost" not in waste.columns:
        waste = waste.copy()
        waste["total_waste_cost"] = 0.0

    merged = purchase.merge(waste, on=keys, how="outer")
    merged["total_purchase_cost"] = merged["total_purchase_cost"].fillna(0.0)
    merged["total_waste_cost"] = merged["total_waste_cost"].fillna(0.0)

    def _ratio(row: pd.Series) -> float:
        purchase_cost = float(row["total_purchase_cost"])
        if purchase_cost <= 0:
            return 0.0
        return float(row["total_waste_cost"]) / purchase_cost

    merged["waste_ratio"] = merged.apply(_ratio, axis=1)
    return merged[[*keys, "waste_ratio"]]


def transform_stockout_frequency(frame: pd.DataFrame) -> pd.DataFrame:
    subset = frame[frame["event_type"] == "stock_threshold_triggered"]
    if subset.empty:
        return pd.DataFrame(
            columns=[
                "location_id",
                "week_start",
                "country",
                "currency",
                "stockout_events_count",
            ]
        )
    grouped = (
        subset.groupby(
            ["location_id", "week_start", "country", "currency"], as_index=False
        )
        .size()
        .rename(columns={"size": "stockout_events_count"})
    )
    return grouped


def transform_price_alert_frequency(frame: pd.DataFrame) -> pd.DataFrame:
    subset = frame[frame["event_type"] == "ingredient_price_variance_detected"]
    if subset.empty:
        return pd.DataFrame(
            columns=[
                "location_id",
                "week_start",
                "country",
                "currency",
                "price_alert_events_count",
            ]
        )
    grouped = (
        subset.groupby(
            ["location_id", "week_start", "country", "currency"], as_index=False
        )
        .size()
        .rename(columns={"size": "price_alert_events_count"})
    )
    return grouped


def merge_weekly_location_performance(
    purchase: pd.DataFrame,
    waste: pd.DataFrame,
    ratio: pd.DataFrame,
    stockout: pd.DataFrame,
    price_alerts: pd.DataFrame,
    *,
    week_starts: list[date] | None = None,
) -> pd.DataFrame:
    """Sparse merge of KPI frames (only grains with at least one signal)."""
    keys = ["location_id", "week_start", "country", "currency"]
    frames = [purchase, waste, ratio, stockout, price_alerts]
    non_empty = [f for f in frames if f is not None and not f.empty]
    if not non_empty:
        return pd.DataFrame(
            columns=[
                *keys,
                "total_purchase_cost",
                "total_waste_cost",
                "waste_ratio",
                "stockout_events_count",
                "price_alert_events_count",
            ]
        )

    merged = non_empty[0]
    for frame in non_empty[1:]:
        merged = merged.merge(frame, on=keys, how="outer")

    for col, default in (
        ("total_purchase_cost", 0.0),
        ("total_waste_cost", 0.0),
        ("waste_ratio", 0.0),
        ("stockout_events_count", 0),
        ("price_alert_events_count", 0),
    ):
        if col not in merged.columns:
            merged[col] = default
        else:
            merged[col] = merged[col].fillna(default)

    if week_starts is not None:
        merged = merged[merged["week_start"].isin(week_starts)]

    # Recompute ratio after outer merge fill.
    merged["waste_ratio"] = merged.apply(
        lambda row: (
            0.0
            if float(row["total_purchase_cost"]) <= 0
            else float(row["total_waste_cost"]) / float(row["total_purchase_cost"])
        ),
        axis=1,
    )
    merged["stockout_events_count"] = merged["stockout_events_count"].astype(int)
    merged["price_alert_events_count"] = merged["price_alert_events_count"].astype(int)
    return merged.sort_values(["week_start", "location_id"]).reset_index(drop=True)


def compute_weekly_kpis(
    rows: list[dict[str, Any]],
    *,
    week_starts: list[date] | None = None,
) -> tuple[pd.DataFrame, int]:
    """Full transform path. Returns (kpi_frame, records_skipped_missing_cost)."""
    frame = events_to_frame(rows)
    if week_starts is not None and not frame.empty:
        frame = frame[frame["week_start"].isin(week_starts)]

    purchase, skip_p = transform_purchase_cost(frame)
    waste, skip_w = transform_waste_cost(frame)
    ratio = transform_waste_ratio(purchase, waste)
    stockout = transform_stockout_frequency(frame)
    price_alerts = transform_price_alert_frequency(frame)
    merged = merge_weekly_location_performance(
        purchase,
        waste,
        ratio,
        stockout,
        price_alerts,
        week_starts=week_starts,
    )
    return merged, skip_p + skip_w
