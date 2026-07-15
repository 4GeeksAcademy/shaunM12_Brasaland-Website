"""Validate and emit telemetry events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from .constants import (
    country_for_location,
    currency_for_location,
    event_definition,
    is_restricted_event,
    processing_for,
    telemetry_enabled,
)
from .context import EmitContext
from .sinks import write_postgres, write_stdout


class TelemetryValidationError(ValueError):
    """Raised when event properties violate the schema allowlist."""


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _validate_properties(event_type: str, properties: dict[str, Any]) -> dict[str, Any]:
    definition = event_definition(event_type)
    allowlist = set(definition.get("propertyAllowlist", []))
    extra = set(properties) - allowlist
    if extra:
        raise TelemetryValidationError(
            f"Event {event_type!r} rejects unknown properties: {sorted(extra)}"
        )
    return properties


def enrich_properties(properties: dict[str, Any]) -> dict[str, Any]:
    """Derive server-side fields such as currency and country before persistence."""
    enriched = dict(properties)
    location_id = enriched.get("location_id")
    if location_id is not None:
        loc = int(location_id)
        if "currency" not in enriched:
            enriched["currency"] = currency_for_location(loc)
        if "country" not in enriched:
            enriched["country"] = country_for_location(loc)
    return enriched


def build_envelope(
    event_type: str,
    properties: dict[str, Any],
    ctx: EmitContext,
) -> dict[str, Any]:
    definition = event_definition(event_type)
    validated = _validate_properties(event_type, properties)
    validated = enrich_properties(validated)
    return {
        "eventId": str(uuid.uuid4()),
        "timestamp": _utc_iso(),
        "sessionId": ctx.session_id,
        "userId": ctx.user_id,
        "event_type": event_type,
        "schemaVersion": int(definition.get("schemaVersion", 1)),
        "requestId": ctx.request_id,
        "service": "api",
        "processing": processing_for(event_type),
        "properties": validated,
    }


def emit_event(
    event_type: str,
    properties: dict[str, Any],
    ctx: EmitContext | None = None,
    *,
    session: Session | None = None,
) -> dict[str, Any] | None:
    """Validate, envelope, and route an event. Returns envelope when emitted."""
    if not telemetry_enabled():
        return None

    context = ctx or EmitContext()
    envelope = build_envelope(event_type, properties, context)
    restricted = is_restricted_event(event_type, envelope["properties"])

    write_stdout(envelope, restricted=restricted)
    if session is not None:
        write_postgres(session, envelope, restricted=restricted)

    return envelope
