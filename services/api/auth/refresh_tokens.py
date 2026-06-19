"""Persistence and rotation logic for refresh tokens.

Refresh tokens are opaque random strings. Only their SHA-256 hash is stored, so
a database leak never exposes a usable token. Tokens are grouped into a
``family`` (all rotations of one login share a ``family_id``) which lets us
detect reuse of an already-rotated token and revoke the whole family.

Tables are resolved lazily via ``database`` so test fixtures can swap the DB
path with a simple ``importlib.reload(database)``.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from tinydb import Query

import config
import database
from .security import generate_opaque_token, hash_opaque_token


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expiry() -> datetime:
    return _now() + timedelta(days=config.REFRESH_TOKEN_EXPIRES_DAYS)


def _is_expired(record: dict[str, Any]) -> bool:
    try:
        expires_at = datetime.fromisoformat(record["expires_at"])
    except (KeyError, ValueError):
        return True
    return expires_at <= _now()


def _find_by_raw(raw_token: str) -> dict[str, Any] | None:
    table = database.get_refresh_tokens_table()
    matches = table.search(Query().token_hash == hash_opaque_token(raw_token))
    return matches[0] if matches else None


def issue_refresh_token(user_id: int, *, family_id: str | None = None) -> str:
    """Create and store a refresh token, returning the raw value for the client."""
    table = database.get_refresh_tokens_table()
    raw_token = generate_opaque_token()
    record = {
        "user_id": user_id,
        "token_hash": hash_opaque_token(raw_token),
        "family_id": family_id or secrets.token_hex(16),
        "expires_at": _expiry().isoformat(),
        "revoked": False,
        "created_at": _now().isoformat(),
    }
    table.insert(record)
    return raw_token


def rotate_refresh_token(raw_token: str) -> tuple[str, int] | None:
    """Validate and rotate a refresh token.

    Returns ``(new_raw_token, user_id)`` on success, or ``None`` when the token
    is unknown, expired, or reused. On reuse of a revoked token the whole family
    is revoked (likely theft).
    """
    table = database.get_refresh_tokens_table()
    record = _find_by_raw(raw_token)
    if record is None:
        return None

    if record.get("revoked"):
        # Reuse of an already-rotated/revoked token → revoke the entire family.
        revoke_family(record.get("family_id"))
        return None

    if _is_expired(record):
        table.update({"revoked": True}, doc_ids=[record.doc_id])
        return None

    table.update({"revoked": True}, doc_ids=[record.doc_id])
    new_raw = issue_refresh_token(record["user_id"], family_id=record.get("family_id"))
    return new_raw, record["user_id"]


def revoke_refresh_token(raw_token: str) -> None:
    """Revoke a single refresh token (used on logout). No-op if unknown."""
    table = database.get_refresh_tokens_table()
    record = _find_by_raw(raw_token)
    if record is not None:
        table.update({"revoked": True}, doc_ids=[record.doc_id])


def revoke_family(family_id: str | None) -> None:
    if family_id is None:
        return
    table = database.get_refresh_tokens_table()
    table.update({"revoked": True}, Query().family_id == family_id)


def revoke_all_for_user(user_id: int) -> int:
    """Revoke every refresh token for a user (logout-all). Returns count touched."""
    table = database.get_refresh_tokens_table()
    matches = table.search(Query().user_id == user_id)
    if matches:
        table.update({"revoked": True}, Query().user_id == user_id)
    return len(matches)


__all__ = [
    "issue_refresh_token",
    "rotate_refresh_token",
    "revoke_refresh_token",
    "revoke_family",
    "revoke_all_for_user",
]
