"""Persistence for password-reset tokens.

A reset token is a signed JWT (see ``auth/security.py``). Only its unique ``jti``
is stored here, alongside a single-use ``used`` flag and an expiry — so a reset
link can be invalidated server-side and **cannot be used twice**. The JWT itself
is never persisted.

Tables are resolved lazily via ``database`` so test fixtures can swap the DB path
with a simple ``importlib.reload(database)``.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from tinydb import Query

import config
import database
from .security import create_password_reset_token


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expiry() -> datetime:
    return _now() + timedelta(minutes=config.PASSWORD_RESET_EXPIRES_MINUTES)


def _is_expired(record: dict[str, Any]) -> bool:
    try:
        expires_at = datetime.fromisoformat(record["expires_at"])
    except (KeyError, ValueError):
        return True
    return expires_at <= _now()


def issue_reset_token(user_id: int) -> str:
    """Store a new reset ``jti`` and return the signed JWT for the email link."""
    table = database.get_password_resets_table()
    jti = secrets.token_hex(16)
    table.insert(
        {
            "user_id": user_id,
            "jti": jti,
            "used": False,
            "expires_at": _expiry().isoformat(),
            "created_at": _now().isoformat(),
        }
    )
    return create_password_reset_token(user_id, jti)


def consume_reset_token(jti: str) -> bool:
    """Mark a reset token used. Returns ``True`` only if it was valid and unused."""
    table = database.get_password_resets_table()
    matches = table.search(Query().jti == jti)
    if not matches:
        return False
    record = matches[0]
    if record.get("used") or _is_expired(record):
        return False
    table.update({"used": True}, doc_ids=[record.doc_id])
    return True


def supersede_user_tokens(user_id: int) -> None:
    """Invalidate a user's outstanding unused tokens so only the latest works."""
    table = database.get_password_resets_table()
    table.update(
        {"used": True},
        (Query().user_id == user_id) & (Query().used == False),  # noqa: E712
    )


__all__ = ["issue_reset_token", "consume_reset_token", "supersede_user_tokens"]
