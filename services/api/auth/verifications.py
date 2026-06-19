"""Persistence for email-verification tokens.

Tokens are opaque random strings; only their SHA-256 hash is stored. Each token
is single-use and time-limited.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from tinydb import Query

import config
import database
from .security import generate_opaque_token, hash_opaque_token


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expiry() -> datetime:
    return _now() + timedelta(hours=config.EMAIL_VERIFICATION_EXPIRES_HOURS)


def _is_expired(record: dict[str, Any]) -> bool:
    try:
        expires_at = datetime.fromisoformat(record["expires_at"])
    except (KeyError, ValueError):
        return True
    return expires_at <= _now()


def issue_verification_token(user_id: int) -> str:
    """Create and store a verification token, returning the raw value."""
    table = database.get_email_verifications_table()
    raw_token = generate_opaque_token()
    table.insert(
        {
            "user_id": user_id,
            "token_hash": hash_opaque_token(raw_token),
            "expires_at": _expiry().isoformat(),
            "used": False,
            "created_at": _now().isoformat(),
        }
    )
    return raw_token


def consume_verification_token(raw_token: str) -> int | None:
    """Validate and consume a token, returning the ``user_id`` or ``None``."""
    table = database.get_email_verifications_table()
    matches = table.search(Query().token_hash == hash_opaque_token(raw_token))
    if not matches:
        return None
    record = matches[0]
    if record.get("used") or _is_expired(record):
        return None
    table.update({"used": True}, doc_ids=[record.doc_id])
    return record["user_id"]


__all__ = ["issue_verification_token", "consume_verification_token"]
