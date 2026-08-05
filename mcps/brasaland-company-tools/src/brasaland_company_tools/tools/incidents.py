"""``manage_incident_tickets`` MCP tool (P24-L6, P24-L13)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .. import errors
from ..scopes import require_scope
from ..upstream import map_upstream_failure, request_json

IncidentAction = Literal["create", "update_status", "get", "list", "summary"]

READ_ACTIONS = frozenset({"get", "list", "summary"})
WRITE_ACTIONS = frozenset({"create", "update_status"})


class IncidentFilters(BaseModel):
    status: str | None = Field(
        default=None,
        description="Filter by lifecycle status: open, in_progress, resolved, discarded.",
    )
    origin: str | None = Field(
        default=None,
        description="Filter by origin: customer, branch, internal.",
    )
    branch: str | None = Field(
        default=None,
        description="Filter by canonical branch slug, e.g. miami_doral.",
    )
    category: str | None = Field(
        default=None,
        description="Filter by category, e.g. equipment_failure, supply_issue.",
    )


class IncidentCreatePayload(BaseModel):
    title: str = Field(min_length=1, description="Short incident title.")
    description: str = Field(min_length=1, description="Detailed incident description.")
    category: str = Field(description="Incident category slug.")
    origin: str = Field(description="Origin: customer, branch, or internal.")
    branch: str = Field(description="Canonical branch slug, e.g. miami_doral.")
    status: str | None = Field(
        default=None,
        description="Initial status; defaults to open when omitted.",
    )


def _success(action: str, data: Any) -> dict[str, Any]:
    return {"ok": True, "action": action, "data": data}


def _validate_action(action: str) -> dict[str, Any] | None:
    allowed = READ_ACTIONS | WRITE_ACTIONS
    if action not in allowed:
        return errors.error_payload(
            errors.VALIDATION_ERROR,
            f"Invalid action '{action}'. Allowed: {', '.join(sorted(allowed))}.",
            details={"field": "action"},
        )
    return None


def manage_incident_tickets(
    action: IncidentAction,
    incident_id: int | None = None,
    status: str | None = None,
    filters: IncidentFilters | None = None,
    payload: IncidentCreatePayload | None = None,
) -> dict[str, Any]:
    """Create, update status, query, or summarize Brasaland incident tickets."""
    invalid = _validate_action(action)
    if invalid:
        return invalid

    if action in READ_ACTIONS:
        scope_error = require_scope("incidents:read")
    else:
        scope_error = require_scope("incidents:write")
    if scope_error:
        return scope_error

    if action == "get":
        return _handle_get(incident_id)
    if action == "list":
        return _handle_list(filters)
    if action == "summary":
        return _handle_summary()
    if action == "create":
        return _handle_create(payload)
    return _handle_update_status(incident_id, status)


def _handle_get(incident_id: int | None) -> dict[str, Any]:
    if incident_id is None:
        return errors.error_payload(
            errors.VALIDATION_ERROR,
            "incident_id is required for action=get.",
            details={"field": "incident_id"},
        )
    status_code, body, transport_error = request_json("GET", f"/incidents/{incident_id}")
    if transport_error or status_code >= 400:
        return map_upstream_failure(
            status=status_code,
            body=body,
            transport_error=transport_error,
            action="get",
        )
    return _success("get", body)


def _handle_list(filters: IncidentFilters | None) -> dict[str, Any]:
    params: dict[str, str] = {}
    if filters:
        for key in ("status", "origin", "branch", "category"):
            value = getattr(filters, key)
            if value:
                params[key] = value
    status_code, body, transport_error = request_json("GET", "/incidents", params=params or None)
    if transport_error or status_code >= 400:
        return map_upstream_failure(
            status=status_code,
            body=body,
            transport_error=transport_error,
            action="list",
        )
    return _success("list", body)


def _handle_summary() -> dict[str, Any]:
    status_code, body, transport_error = request_json("GET", "/incidents/summary")
    if transport_error or status_code >= 400:
        return map_upstream_failure(
            status=status_code,
            body=body,
            transport_error=transport_error,
            action="summary",
        )
    return _success("summary", body)


def _handle_create(payload: IncidentCreatePayload | None) -> dict[str, Any]:
    if payload is None:
        return errors.error_payload(
            errors.VALIDATION_ERROR,
            "payload is required for action=create.",
            details={"field": "payload"},
        )
    body = payload.model_dump(exclude_none=True)
    status_code, response_body, transport_error = request_json(
        "POST",
        "/incidents",
        json_body=body,
    )
    if transport_error or status_code >= 400:
        return map_upstream_failure(
            status=status_code,
            body=response_body,
            transport_error=transport_error,
            action="create",
        )
    return _success("create", response_body)


def _handle_update_status(incident_id: int | None, status: str | None) -> dict[str, Any]:
    if incident_id is None:
        return errors.error_payload(
            errors.VALIDATION_ERROR,
            "incident_id is required for action=update_status.",
            details={"field": "incident_id"},
        )
    if not status:
        return errors.error_payload(
            errors.VALIDATION_ERROR,
            "status is required for action=update_status.",
            details={"field": "status"},
        )
    status_code, body, transport_error = request_json(
        "PATCH",
        f"/incidents/{incident_id}/status",
        json_body={"status": status},
    )
    if transport_error or status_code >= 400:
        return map_upstream_failure(
            status=status_code,
            body=body,
            transport_error=transport_error,
            action="update_status",
        )
    return _success("update_status", body)
