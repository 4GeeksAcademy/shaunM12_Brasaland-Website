"""Template confirmations for incident writes (P24-OPT-J6)."""

from __future__ import annotations

from typing import Any


def format_create_confirmation(row: dict[str, Any]) -> str:
    incident_id = row.get("id", "?")
    title = row.get("title") or "(no title)"
    status = row.get("status") or "open"
    branch = row.get("branch") or "unknown"
    return (
        f"Incident #{incident_id} created successfully. "
        f"Title: {title}. Status: {status}. Branch: {branch}."
    )


def format_update_confirmation(row: dict[str, Any]) -> str:
    incident_id = row.get("id", "?")
    status = row.get("status") or "unknown"
    return f"Incident #{incident_id} status updated to {status}."


def format_write_confirmation(envelope: dict[str, Any]) -> str:
    """Build a template answer from a successful mutate envelope."""
    action = envelope.get("action")
    rows = envelope.get("rows") or []
    if not rows:
        raise ValueError("Write confirmation requires at least one row.")
    row = rows[0]
    if action == "create":
        return format_create_confirmation(row)
    if action == "update_status":
        return format_update_confirmation(row)
    raise ValueError(f"Unsupported write action for confirmation: {action}")
