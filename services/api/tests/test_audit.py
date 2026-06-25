"""Pure-function unit tests for ``auth/audit.py``.

The reset-request rate limit depends entirely on ``recent_request_count``
correctly counting events for *one* email inside a rolling time window. Tested
directly against a throwaway DB.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from auth import audit


def test_records_and_counts_requests_for_an_email(db):
    audit.record_event(audit.REQUESTED, "a@brasaland.com")
    audit.record_event(audit.REQUESTED, "a@brasaland.com")
    assert audit.recent_request_count("a@brasaland.com") == 2


def test_count_is_scoped_per_email(db):
    audit.record_event(audit.REQUESTED, "a@brasaland.com")
    audit.record_event(audit.REQUESTED, "b@brasaland.com")
    assert audit.recent_request_count("a@brasaland.com") == 1
    assert audit.recent_request_count("b@brasaland.com") == 1


def test_completed_events_do_not_count_as_requests(db):
    audit.record_event(audit.COMPLETED, "a@brasaland.com")
    assert audit.recent_request_count("a@brasaland.com") == 0


def test_events_outside_the_window_are_excluded(db):
    # An old request (2 hours ago) must fall outside the default 1-hour window.
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    db.get_auth_audit_table().insert(
        {
            "event": audit.REQUESTED,
            "email": "a@brasaland.com",
            "user_id": None,
            "ip": None,
            "created_at": old,
        }
    )
    audit.record_event(audit.REQUESTED, "a@brasaland.com")  # recent

    assert audit.recent_request_count("a@brasaland.com") == 1
    # Widening the window picks the old one back up.
    assert audit.recent_request_count("a@brasaland.com", within_hours=3) == 2


def test_unknown_email_counts_zero(db):
    assert audit.recent_request_count("nobody@brasaland.com") == 0
