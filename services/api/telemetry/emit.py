"""Validate and emit telemetry events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from .constants import (
    currency_for_location,
    event_definition,
    is_restricted_consumption,
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


def _inject_currency(properties: dict[str, Any]) -> dict[str, Any]:
    location_id = properties.get("location_id")
    if location_id is not None and "currency" not in properties:
        enriched = dict(properties)
        enriched["currency"] = currency_for_location(int(location_id))
        return enriched
    return properties


def build_envelope(
    event_type: str,
    properties: dict[str, Any],
    ctx: EmitContext,
) -> dict[str, Any]:
    definition = event_definition(event_type)
    validated = _validate_properties(event_type, properties)
    validated = _inject_currency(validated)
    return {
        "eventId": str(uuid.uuid4()),
        "timestamp": _utc_iso(),
        "sessionId": ctx.session_id,
        "userId": ctx.user_id,
        "event_type": event_type,
        "schemaVersion": int(definition.get("schemaVersion", 1)),
        "requestId": ctx.request_id,
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
    restricted = (
        event_type == "consumption_order_created"
        and is_restricted_consumption(envelope["properties"])
    )

    write_stdout(envelope, restricted=restricted)
    if session is not None:
        write_postgres(session, envelope, restricted=restricted)

    return envelope
