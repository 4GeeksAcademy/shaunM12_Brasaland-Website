"""Incident lookup tool — HTTP to bare FastAPI ``/incidents`` (P2-L3, P2-L36)."""

from __future__ import annotations

from typing import Any

from .http import fetch_json

INCIDENTS_SOURCE = "incidents_api"


def _normalize_row(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "description": raw.get("description"),
        "status": raw.get("status"),
        "origin": raw.get("origin"),
        "branch": raw.get("branch"),
        "category": raw.get("category"),
    }


def _failure_envelope(
    *,
    http_status: int,
    reason: str,
    error: str | None = None,
    incident_id: int | None = None,
    filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "source": INCIDENTS_SOURCE,
        "ok": False,
        "http_status": http_status,
        "rows": [],
        "error": error or reason,
        "reason": reason,
    }
    if incident_id is not None:
        envelope["incident_id"] = incident_id
    if filters:
        envelope["filters"] = filters
    return envelope


def lookup_incidents(
    *,
    incident_id: int | None,
    filters: dict[str, str] | None,
    auth_header: str | None,
) -> dict[str, Any]:
    """Call incidents API and return a P2-L36 envelope."""
    filter_copy = dict(filters or {})
    headers: dict[str, str] = {}
    if auth_header:
        headers["Authorization"] = auth_header

    if incident_id is not None:
        status, body, transport_reason = fetch_json(
            "GET",
            f"/incidents/{incident_id}",
            headers=headers,
        )
        if transport_reason == "timeout":
            return _failure_envelope(
                http_status=0,
                reason="timeout",
                incident_id=incident_id,
                filters=filter_copy,
            )
        if transport_reason is not None:
            return _failure_envelope(
                http_status=status,
                reason="http_error",
                incident_id=incident_id,
                filters=filter_copy,
            )
        if status == 404:
            return _failure_envelope(
                http_status=404,
                reason="not_found",
                incident_id=incident_id,
                filters=filter_copy,
            )
        if status >= 400:
            return _failure_envelope(
                http_status=status,
                reason=f"http_{status}",
                incident_id=incident_id,
                filters=filter_copy,
            )
        if not isinstance(body, dict):
            return _failure_envelope(
                http_status=status,
                reason="invalid_response",
                incident_id=incident_id,
                filters=filter_copy,
            )
        return {
            "source": INCIDENTS_SOURCE,
            "ok": True,
            "http_status": status,
            "incident_id": incident_id,
            "filters": filter_copy,
            "rows": [_normalize_row(body)],
            "error": None,
            "reason": None,
        }

    status, body, transport_reason = fetch_json(
        "GET",
        "/incidents",
        params=filter_copy,
        headers=headers,
    )
    if transport_reason == "timeout":
        return _failure_envelope(
            http_status=0,
            reason="timeout",
            filters=filter_copy,
        )
    if transport_reason is not None:
        return _failure_envelope(
            http_status=status,
            reason="http_error",
            filters=filter_copy,
        )
    if status >= 400:
        return _failure_envelope(
            http_status=status,
            reason=f"http_{status}",
            filters=filter_copy,
        )
    if not isinstance(body, list):
        return _failure_envelope(
            http_status=status,
            reason="invalid_response",
            filters=filter_copy,
        )

    rows = [_normalize_row(item) for item in body if isinstance(item, dict)]
    if not rows:
        return {
            "source": INCIDENTS_SOURCE,
            "ok": True,
            "http_status": status,
            "filters": filter_copy,
            "rows": [],
            "error": None,
            "reason": "empty",
        }

    return {
        "source": INCIDENTS_SOURCE,
        "ok": True,
        "http_status": status,
        "filters": filter_copy,
        "rows": rows,
        "error": None,
        "reason": None,
    }
