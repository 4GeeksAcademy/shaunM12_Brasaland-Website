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


def consumption_by_location_per_day(
    start_date: datetime,
    end_date: datetime,
    *,
    session: Session | None,
) -> list[dict[str, Any]]:
    """Count consumption events per day and location."""
    frame = _query_events(
        session,
        event_types=["consumption_order_created"],
        start_date=start_date,
        end_date=end_date,
    )
    if frame.empty:
        return []

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    frame = _with_tag_columns(frame)
    frame["location_id"] = pd.to_numeric(
        frame.get("tag_location_id"),
        errors="coerce",
    )
    grouped = (
        frame.dropna(subset=["location_id"])
        .groupby(["date", "location_id"], as_index=False)
        .agg(count=("id", "count"))
        .sort_values(["date", "location_id"])
    )
    if grouped.empty:
        return []

    grouped["location_id"] = grouped["location_id"].astype(int)
    grouped["count"] = grouped["count"].astype(int)
    return _records(grouped[["date", "location_id", "count"]])


def order_failure_rate_per_day(
    start_date: datetime,
    end_date: datetime,
    *,
    session: Session | None,
) -> list[dict[str, Any]]:
    """Compute order failure ratio per day across inbound and outbound orders."""
    frame = _query_events(
        session,
        event_types=[
            "consumption_order_created",
            "supply_order_created",
            "consumption_order_failed",
            "supply_order_failed",
        ],
        start_date=start_date,
        end_date=end_date,
    )
    if frame.empty:
        return []

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    frame["is_failure"] = frame["event_type"].str.endswith("_failed")
    grouped = (
        frame.groupby("date", as_index=False)
        .agg(total=("id", "count"), failures=("is_failure", "sum"))
        .sort_values(["date"])
    )
    grouped["failure_rate"] = grouped["failures"] / grouped["total"]
    grouped["total"] = grouped["total"].astype(int)
    grouped["failures"] = grouped["failures"].astype(int)
    return _records(grouped[["date", "total", "failures", "failure_rate"]])


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

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
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

