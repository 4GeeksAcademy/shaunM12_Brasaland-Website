"""Pure-function unit tests for ``auth/dependencies.py``.

``get_current_user`` and ``require_admin`` are the gatekeepers every protected
endpoint relies on. These call them directly (no HTTP) with hand-crafted tokens
and assert on the access decision — and crucially that malformed input yields a
clean ``401`` rather than an unhandled ``500``.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from auth.dependencies import get_current_user, require_admin
from auth.security import create_access_token
from users.models import UserCreate, UserUpdate
from users.repository import create_user, update_user


def _make_user(email: str, *, is_admin: bool = False, is_active: bool = True):
    user = create_user(UserCreate(email=email, password="supersecret"), is_admin=is_admin)
    if not is_active:
        update_user(user.id, UserUpdate(is_active=False))
        user = user.model_copy(update={"is_active": False})
    return user


# --- get_current_user: happy path -------------------------------------------


def test_get_current_user_returns_user_for_valid_token(db):
    user = _make_user("valid@brasaland.com")
    token = create_access_token(user.id)

    resolved = get_current_user(token)
    assert resolved.id == user.id
    assert resolved.email == "valid@brasaland.com"


def test_get_current_user_result_never_exposes_password_hash(db):
    user = _make_user("nohash@brasaland.com")
    resolved = get_current_user(create_access_token(user.id))
    assert not hasattr(resolved, "hashed_password")


# --- get_current_user: failure modes (must be 401, not 500) ------------------


def test_expired_token_is_rejected(db):
    user = _make_user("expired@brasaland.com")
    token = create_access_token(user.id, expires_minutes=-1)
    with pytest.raises(HTTPException) as exc:
        get_current_user(token)
    assert exc.value.status_code == 401


def test_malformed_token_is_rejected(db):
    with pytest.raises(HTTPException) as exc:
        get_current_user("this-is-not-a-jwt")
    assert exc.value.status_code == 401


def test_non_numeric_subject_is_rejected(db):
    """A token whose ``sub`` is not an int must 401, not raise ValueError → 500."""
    token = create_access_token("not-an-int")
    with pytest.raises(HTTPException) as exc:
        get_current_user(token)
    assert exc.value.status_code == 401


def test_unknown_user_is_rejected(db):
    """Valid signature, but the referenced user does not exist."""
    token = create_access_token(999999)
    with pytest.raises(HTTPException) as exc:
        get_current_user(token)
    assert exc.value.status_code == 401


def test_inactive_user_is_rejected(db):
    user = _make_user("inactive@brasaland.com", is_active=False)
    token = create_access_token(user.id)
    with pytest.raises(HTTPException) as exc:
        get_current_user(token)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Inactive user"


# --- require_admin -----------------------------------------------------------


def test_require_admin_allows_admin(db):
    admin = _make_user("admin@brasaland.com", is_admin=True)
    resolved = require_admin(admin)
    assert resolved.id == admin.id


def test_require_admin_blocks_non_admin(db):
    plain = _make_user("plain@brasaland.com", is_admin=False)
    with pytest.raises(HTTPException) as exc:
        require_admin(plain)
    assert exc.value.status_code == 403
