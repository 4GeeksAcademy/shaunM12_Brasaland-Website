"""Telemetry KPI analysis helpers for Phase 4 reporting."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import bindparam, text
from sqlmodel import Session


def _empty_events_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["id", "event_type", "timestamp", "tags"])


def _query_events(
    session: Session | None,
    *,
    event_types: list[str],
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    if session is None:
        return _empty_events_frame()

    statement = text(
        """
        SELECT id, event_type, timestamp, tags
        FROM telemetry_events
        WHERE event_type IN :event_types
          AND timestamp >= :start_date
          AND timestamp < :end_date
        """
    ).bindparams(bindparam("event_types", expanding=True))
    rows = session.execute(
        statement,
        {
            "event_types": event_types,
            "start_date": start_date,
            "end_date": end_date,
        },
    ).mappings().all()
    if not rows:
        return _empty_events_frame()
    return pd.DataFrame(rows)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return json.loads(frame.to_json(orient="records"))


def _with_tag_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    tags = pd.json_normalize(frame["tags"]).add_prefix("tag_")
    return pd.concat([frame.drop(columns=["tags"]), tags], axis=1)


def _prepare_timestamps(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    return frame


def daily_consumption_by_ingredient_and_location(
    start_date: datetime,
    end_date: datetime,
    *,
    session: Session | None,
) -> list[dict[str, Any]]:
    """KPI 1: units consumed per ingredient per location per day (reason=consumption)."""
    frame = _query_events(
        session,
        event_types=["consumption_order_created"],
        start_date=start_date,
        end_date=end_date,
    )
    if frame.empty:
        return []

    frame = _prepare_timestamps(_with_tag_columns(frame))
    frame["location_id"] = pd.to_numeric(frame.get("tag_location_id"), errors="coerce")
    frame["ingredient_id"] = pd.to_numeric(frame.get("tag_ingredient_id"), errors="coerce")
    frame["quantity"] = pd.to_numeric(frame.get("tag_quantity"), errors="coerce")
    frame["reason"] = frame.get("tag_reason")
    frame = frame.loc[frame["reason"].eq("consumption")].dropna(
        subset=["location_id", "ingredient_id", "quantity"]
    )
    if frame.empty:
        return []

    grouped = (
        frame.groupby(["date", "ingredient_id", "location_id"], as_index=False)
        .agg(quantity=("quantity", "sum"))
        .sort_values(["date", "location_id", "ingredient_id"])
    )
    grouped["location_id"] = grouped["location_id"].astype(int)
    grouped["ingredient_id"] = grouped["ingredient_id"].astype(int)
    grouped["quantity"] = grouped["quantity"].astype(float)
    return _records(grouped[["date", "ingredient_id", "location_id", "quantity"]])


def stock_out_frequency(
    start_date: datetime,
    end_date: datetime,
    *,
    session: Session | None,
) -> list[dict[str, Any]]:
    """KPI 2: stock-out signals per ingredient, location, and day."""
    frame = _query_events(
        session,
        event_types=["stock_threshold_triggered", "consumption_order_failed"],
        start_date=start_date,
        end_date=end_date,
    )
    if frame.empty:
        return []

    frame = _prepare_timestamps(_with_tag_columns(frame))
    frame["location_id"] = pd.to_numeric(frame.get("tag_location_id"), errors="coerce")
    frame["ingredient_id"] = pd.to_numeric(frame.get("tag_ingredient_id"), errors="coerce")
    frame["error_code"] = frame.get("tag_error_code")
    is_threshold = frame["event_type"].eq("stock_threshold_triggered")
    is_insufficient_stock = frame["event_type"].eq("consumption_order_failed") & frame[
        "error_code"
    ].eq("insufficient_stock")
    frame = frame.loc[is_threshold | is_insufficient_stock].dropna(
        subset=["location_id", "ingredient_id"]
    )
    if frame.empty:
        return []

    grouped = (
        frame.groupby(["date", "ingredient_id", "location_id"], as_index=False)
        .agg(count=("id", "count"))
        .sort_values(["date", "location_id", "ingredient_id"])
    )
    grouped["location_id"] = grouped["location_id"].astype(int)
    grouped["ingredient_id"] = grouped["ingredient_id"].astype(int)
    grouped["count"] = grouped["count"].astype(int)
    return _records(grouped[["date", "ingredient_id", "location_id", "count"]])


def waste_loss_ratio(
    start_date: datetime,
    end_date: datetime,
    *,
    session: Session | None,
) -> list[dict[str, Any]]:
    """KPI 3: waste quantity as a proportion of total outbound consumption per location/day."""
    frame = _query_events(
        session,
        event_types=["consumption_order_created"],
        start_date=start_date,
        end_date=end_date,
    )
    if frame.empty:
        return []

    frame = _prepare_timestamps(_with_tag_columns(frame))
    frame["location_id"] = pd.to_numeric(frame.get("tag_location_id"), errors="coerce")
    frame["quantity"] = pd.to_numeric(frame.get("tag_quantity"), errors="coerce")
    frame["reason"] = frame.get("tag_reason")
    frame = frame.dropna(subset=["location_id", "quantity"])
    if frame.empty:
        return []

    frame["is_waste"] = frame["reason"].eq("waste")
    frame["waste_quantity_col"] = frame["quantity"].where(frame["is_waste"], 0.0)
    grouped = (
        frame.groupby(["date", "location_id"], as_index=False)
        .agg(
            waste_quantity=("waste_quantity_col", "sum"),
            total_quantity=("quantity", "sum"),
        )
        .sort_values(["date", "location_id"])
    )
    grouped["ratio"] = grouped["waste_quantity"] / grouped["total_quantity"]
    grouped["location_id"] = grouped["location_id"].astype(int)
    grouped["waste_quantity"] = grouped["waste_quantity"].astype(float)
    grouped["total_quantity"] = grouped["total_quantity"].astype(float)
    return _records(
        grouped[["date", "location_id", "waste_quantity", "total_quantity", "ratio"]]
    )


def auth_failure_rate_per_day(
    start_date: datetime,
    end_date: datetime,
    *,
    session: Session | None,
) -> list[dict[str, Any]]:
    """Optional auth quality metric: failed / total login attempts per day."""
    frame = _query_events(
        session,
        event_types=["user_login_succeeded", "user_login_failed"],
        start_date=start_date,
        end_date=end_date,
    )
    if frame.empty:
        return []

    frame = _prepare_timestamps(frame)
    frame["is_failed"] = frame["event_type"].eq("user_login_failed")
    grouped = (
        frame.groupby("date", as_index=False)
        .agg(total=("id", "count"), failed=("is_failed", "sum"))
        .sort_values(["date"])
    )
    grouped["failure_rate"] = grouped["failed"] / grouped["total"]
    grouped["total"] = grouped["total"].astype(int)
    grouped["failed"] = grouped["failed"].astype(int)
    return _records(grouped[["date", "total", "failed", "failure_rate"]])
