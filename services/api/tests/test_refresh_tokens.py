"""Pure-function unit tests for ``auth/refresh_tokens.py``.

Refresh-token rotation is the trickiest piece of session logic: it must rotate
on use, detect reuse of an already-rotated token (theft), and honour expiry.
Tested directly against a throwaway DB, with no HTTP layer.
"""

from __future__ import annotations

import config
from auth import refresh_tokens


def test_issue_then_rotate_returns_new_token_and_user(db):
    raw = refresh_tokens.issue_refresh_token(user_id=1)
    rotated = refresh_tokens.rotate_refresh_token(raw)
    assert rotated is not None
    new_raw, user_id = rotated
    assert user_id == 1
    assert new_raw != raw


def test_rotated_token_cannot_be_used_again(db):
    raw = refresh_tokens.issue_refresh_token(user_id=1)
    refresh_tokens.rotate_refresh_token(raw)
    # The original token is now revoked → reuse must fail.
    assert refresh_tokens.rotate_refresh_token(raw) is None


def test_unknown_token_is_rejected(db):
    assert refresh_tokens.rotate_refresh_token("never-issued") is None


def test_expired_token_is_rejected(db, monkeypatch):
    """A token whose stored expiry is in the past must not rotate."""
    monkeypatch.setattr(config, "REFRESH_TOKEN_EXPIRES_DAYS", -1)
    raw = refresh_tokens.issue_refresh_token(user_id=1)
    assert refresh_tokens.rotate_refresh_token(raw) is None


def test_reuse_of_revoked_token_revokes_whole_family(db):
    """Replaying a rotated token is treated as theft: the new token dies too."""
    raw = refresh_tokens.issue_refresh_token(user_id=1)
    rotated = refresh_tokens.rotate_refresh_token(raw)
    assert rotated is not None
    new_raw, _ = rotated

    # Attacker replays the old (already-rotated) token.
    assert refresh_tokens.rotate_refresh_token(raw) is None
    # As a result the legitimate new token from the same family is now revoked.
    assert refresh_tokens.rotate_refresh_token(new_raw) is None


def test_revoke_refresh_token_makes_it_unusable(db):
    raw = refresh_tokens.issue_refresh_token(user_id=1)
    refresh_tokens.revoke_refresh_token(raw)
    assert refresh_tokens.rotate_refresh_token(raw) is None


def test_revoke_refresh_token_unknown_is_noop(db):
    # Should not raise.
    refresh_tokens.revoke_refresh_token("never-issued")


def test_revoke_all_for_user_counts_and_kills_sessions(db):
    refresh_tokens.issue_refresh_token(user_id=1)
    refresh_tokens.issue_refresh_token(user_id=1)
    other = refresh_tokens.issue_refresh_token(user_id=2)

    count = refresh_tokens.revoke_all_for_user(1)
    assert count == 2
    # User 2's token is untouched.
    assert refresh_tokens.rotate_refresh_token(other) is not None


def test_revoke_family_none_is_noop(db):
    refresh_tokens.revoke_family(None)  # should not raise
