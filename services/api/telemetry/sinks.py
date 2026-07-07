"""Telemetry output destinations."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlmodel import Session

from .constants import sink_includes_postgres, sink_includes_stdout
from .models import TelemetryEvent, TelemetryEventRestricted

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
    row_kwargs = {
        "event_id": envelope["eventId"],
        "timestamp": timestamp,
        "session_id": envelope["sessionId"],
        "user_id": envelope["userId"],
        "event_type": envelope["event_type"],
        "schema_version": envelope["schemaVersion"],
        "request_id": envelope["requestId"],
        "processing": envelope["processing"],
        "properties": envelope["properties"],
    }
    model = TelemetryEventRestricted if restricted else TelemetryEvent
    session.add(model(**row_kwargs))
    session.commit()
