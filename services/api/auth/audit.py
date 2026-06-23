"""Audit log for password events + reset-request rate limiting.

Records auth-sensitive events (event, email, user_id, IP, timestamp) and counts
recent reset requests per email to enforce an hourly rate limit. Tokens are
never stored here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tinydb import Query

import database

REQUESTED = "password_reset_requested"
COMPLETED = "password_reset_completed"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record_event(
    event: str,
    email: str,
    user_id: int | None = None,
    ip: str | None = None,
) -> None:
    """Append an audit row. ``user_id`` is ``None`` for unknown emails."""
    database.get_auth_audit_table().insert(
        {
            "event": event,
            "email": email,
            "user_id": user_id,
            "ip": ip,
            "created_at": _now().isoformat(),
        }
    )


def recent_request_count(email: str, within_hours: int = 1) -> int:
    """Count ``password_reset_requested`` rows for an email in the last window."""
    table = database.get_auth_audit_table()
    cutoff = _now() - timedelta(hours=within_hours)
    rows = table.search((Query().event == REQUESTED) & (Query().email == email))
    count = 0
    for row in rows:
        try:
            created = datetime.fromisoformat(row["created_at"])
        except (KeyError, ValueError):
            continue
        if created >= cutoff:
            count += 1
    return count


__all__ = ["REQUESTED", "COMPLETED", "record_event", "recent_request_count"]
