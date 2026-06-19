"""TinyDB persistence layer for users.

The DB table is resolved lazily via ``database.get_users_table()`` (rather than a
module-level import) so test fixtures can swap the database path with a simple
``importlib.reload(database)`` without re-importing this module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from tinydb import Query

import database
from auth.security import hash_password
from .models import UserCreate, UserInDB, UserResponse, UserUpdate


class EmailAlreadyExistsError(ValueError):
    """Raised when creating/updating a user with an email that is already taken."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _to_response(record: dict[str, Any]) -> UserResponse:
    return UserResponse.model_validate(record)


def _to_db(record: dict[str, Any]) -> UserInDB:
    return UserInDB.model_validate(record)


def get_user_record_by_email(email: str) -> UserInDB | None:
    """Return the stored user (incl. ``hashed_password``) or ``None``."""
    table = database.get_users_table()
    matches = table.search(Query().email == _normalize_email(email))
    return _to_db(matches[0]) if matches else None


def get_user_record(user_id: int) -> UserInDB | None:
    """Return the stored user (incl. ``hashed_password``) or ``None``."""
    record = database.get_users_table().get(doc_id=user_id)
    return _to_db(record) if record is not None else None


def create_user(payload: UserCreate, *, is_admin: bool = False) -> UserResponse:
    table = database.get_users_table()
    email = _normalize_email(payload.email)
    if get_user_record_by_email(email) is not None:
        raise EmailAlreadyExistsError("Email already registered")

    record = {
        "email": email,
        "name": payload.name,
        "hashed_password": hash_password(payload.password),
        "is_active": True,
        "is_admin": is_admin,
        "is_verified": False,
        "created_at": _utc_now_iso(),
    }
    doc_id = table.insert(record)
    table.update({"id": doc_id}, doc_ids=[doc_id])
    stored = table.get(doc_id=doc_id)
    if stored is None:
        raise RuntimeError("Failed to persist user")
    return _to_response(stored)


def list_users() -> list[UserResponse]:
    records = database.get_users_table().all()
    records.sort(key=lambda row: row.get("email", ""))
    return [_to_response(row) for row in records]


def get_user(user_id: int) -> UserResponse | None:
    record = get_user_record(user_id)
    return UserResponse.model_validate(record.model_dump()) if record is not None else None


def update_user(user_id: int, payload: UserUpdate) -> UserResponse | None:
    table = database.get_users_table()
    record = table.get(doc_id=user_id)
    if record is None:
        return None

    changes: dict[str, Any] = {}
    if payload.email is not None:
        new_email = _normalize_email(payload.email)
        existing = get_user_record_by_email(new_email)
        if existing is not None and existing.id != user_id:
            raise EmailAlreadyExistsError("Email already registered")
        changes["email"] = new_email
    if payload.password is not None:
        changes["hashed_password"] = hash_password(payload.password)
    if payload.name is not None:
        changes["name"] = payload.name
    if payload.is_active is not None:
        changes["is_active"] = payload.is_active
    if payload.is_admin is not None:
        changes["is_admin"] = payload.is_admin

    if changes:
        table.update(changes, doc_ids=[user_id])
    updated = table.get(doc_id=user_id)
    return _to_response(updated) if updated else None


def mark_verified(user_id: int) -> UserResponse | None:
    """Flag a user's email as verified."""
    table = database.get_users_table()
    if table.get(doc_id=user_id) is None:
        return None
    table.update({"is_verified": True}, doc_ids=[user_id])
    updated = table.get(doc_id=user_id)
    return _to_response(updated) if updated else None


def delete_user(user_id: int) -> bool:
    table = database.get_users_table()
    if table.get(doc_id=user_id) is None:
        return False
    table.remove(doc_ids=[user_id])
    return True
