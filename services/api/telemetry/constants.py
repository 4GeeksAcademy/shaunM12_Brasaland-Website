"""Telemetry configuration and schema helpers."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import config
from inventory.constants import country_for_location

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMAS_PATH = REPO_ROOT / "docs" / "telemetry" / "event-schemas.json"

STOCK_MUTATION_FIELDS = frozenset(
    {"current_stock", "stock", "min_stock_threshold", "quantity"}
)

ANONYMOUS_USER_ID = "anonymous"


def currency_for_location(location_id: int) -> str:
    """Derive ISO currency from restaurant location (1–9 COP, 10–14 USD)."""
    return "COP" if country_for_location(location_id) == "CO" else "USD"


@lru_cache(maxsize=1)
def load_event_schemas() -> dict[str, Any]:
    with SCHEMAS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def event_definition(event_type: str) -> dict[str, Any]:
    schemas = load_event_schemas()
    events = schemas.get("events", {})
    if event_type not in events:
        raise KeyError(f"Unknown telemetry event_type: {event_type}")
    return events[event_type]


def processing_for(event_type: str) -> str:
    return str(event_definition(event_type).get("processing", "batch"))


def is_restricted_consumption(properties: dict[str, Any]) -> bool:
    return properties.get("reason") == "theft"


def telemetry_enabled() -> bool:
    return config.TELEMETRY_ENABLED


def sink_includes_stdout() -> bool:
    return config.TELEMETRY_SINK in {"stdout", "both"}


def sink_includes_postgres() -> bool:
    return config.TELEMETRY_SINK in {"postgres", "both"} and bool(config.DATABASE_URL)
