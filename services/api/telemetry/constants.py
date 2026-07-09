"""Telemetry configuration and schema helpers."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import config
from inventory.constants import country_for_location


def _resolve_schemas_path() -> Path:
    """Locate event-schemas.json across local and Docker layouts."""
    env_override = os.getenv("TELEMETRY_SCHEMAS_PATH")
    if env_override:
        candidate = Path(env_override).expanduser()
        if candidate.exists():
            return candidate

    here = Path(__file__).resolve()
    candidates: list[Path] = []
    for parent in (here.parent, *here.parents):
        candidates.append(parent / "docs" / "telemetry" / "event-schemas.json")
        candidates.append(parent / "telemetry" / "event-schemas.json")

    # Common docker-compose path when docs are mounted into backend.
    candidates.append(Path("/app/docs/telemetry/event-schemas.json"))

    for candidate in candidates:
        if candidate.exists():
            return candidate

    searched = "\n".join(f"- {path}" for path in candidates)
    raise RuntimeError(
        "Could not locate docs/telemetry/event-schemas.json.\n"
        "Set TELEMETRY_SCHEMAS_PATH or ensure docs are mounted in Docker.\n"
        f"Searched:\n{searched}"
    )


SCHEMAS_PATH = _resolve_schemas_path()

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
    # Milestone 5 baseline reasons are consumption/waste, so restricted routing
    # is inactive unless future phases reintroduce restricted reason values.
    return properties.get("reason") == "__restricted__"


def telemetry_enabled() -> bool:
    return config.TELEMETRY_ENABLED


def sink_includes_stdout() -> bool:
    return config.TELEMETRY_SINK in {"stdout", "both"}


def sink_includes_postgres() -> bool:
    return config.TELEMETRY_SINK in {"postgres", "both"} and bool(config.DATABASE_URL)
