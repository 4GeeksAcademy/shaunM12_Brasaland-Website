"""Telemetry output destinations."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlmodel import Session

from .constants import sink_includes_postgres, sink_includes_stdout
from .models import TelemetryEvent

logger = logging.getLogger("brasaland.telemetry")


def write_stdout(envelope: dict[str, Any], *, restricted: bool) -> None:
    if not sink_includes_stdout():
        return
    payload = {
        **envelope,
        "_sink": "restricted" if restricted else "standard",
    }
    logger.info("telemetry_event %s", json.dumps(payload, default=str))


def write_postgres(
    session: Session,
    envelope: dict[str, Any],
    *,
    restricted: bool,
) -> None:
    if not sink_includes_postgres():
        return
    timestamp = datetime.fromisoformat(envelope["timestamp"].replace("Z", "+00:00"))
    tags = envelope["properties"]
    quantity = tags.get("quantity")
    quantity_requested = tags.get("quantity_requested")
    raw_value = quantity if quantity is not None else quantity_requested
    value: float | None
    if isinstance(raw_value, (int, float)):
        value = float(raw_value)
    else:
        value = None

    row = TelemetryEvent(
        event_type=envelope["event_type"],
        timestamp=timestamp,
        service=str(envelope.get("service", "api")),
        level="restricted" if restricted else "info",
        value=value,
        tags=tags,
    )
    session.add(row)
    session.commit()
