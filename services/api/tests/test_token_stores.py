"""Pure-function unit tests for the single-use token stores.

Covers ``auth/verifications.py`` (opaque email-verification tokens) and
``auth/password_resets.py`` (reset ``jti`` records). Both must be single-use and
time-limited; tested directly against a throwaway DB.
"""

from __future__ import annotations

import config
from auth import password_resets, verifications


# --- Email verification tokens ----------------------------------------------


def test_verification_token_consumes_once_and_returns_user(db):
    raw = verifications.issue_verification_token(user_id=7)
    assert verifications.consume_verification_token(raw) == 7


def test_verification_token_is_single_use(db):
    raw = verifications.issue_verification_token(user_id=7)
    assert verifications.consume_verification_token(raw) == 7
    # Second use is rejected.
    assert verifications.consume_verification_token(raw) is None


def test_unknown_verification_token_is_rejected(db):
    assert verifications.consume_verification_token("never-issued") is None


def test_expired_verification_token_is_rejected(db, monkeypatch):
    monkeypatch.setattr(config, "EMAIL_VERIFICATION_EXPIRES_HOURS", -1)
    raw = verifications.issue_verification_token(user_id=7)
    assert verifications.consume_verification_token(raw) is None


# --- Password-reset jti store ------------------------------------------------


def test_reset_token_consumes_once(db):
    # ``issue_reset_token`` returns the signed JWT; the jti is what we consume.
    table = db.get_password_resets_table()
    password_resets.issue_reset_token(user_id=3)
    jti = table.all()[0]["jti"]
    assert password_resets.consume_reset_token(jti) is True


def test_reset_token_is_single_use(db):
    table = db.get_password_resets_table()
    password_resets.issue_reset_token(user_id=3)
    jti = table.all()[0]["jti"]
    assert password_resets.consume_reset_token(jti) is True
    assert password_resets.consume_reset_token(jti) is False


def test_unknown_reset_jti_is_rejected(db):
    assert password_resets.consume_reset_token("no-such-jti") is False


def test_expired_reset_token_is_rejected(db, monkeypatch):
    monkeypatch.setattr(config, "PASSWORD_RESET_EXPIRES_MINUTES", -1)
    table = db.get_password_resets_table()
    password_resets.issue_reset_token(user_id=3)
    jti = table.all()[0]["jti"]
    assert password_resets.consume_reset_token(jti) is False


def test_supersede_invalidates_outstanding_tokens(db):
    table = db.get_password_resets_table()
    password_resets.issue_reset_token(user_id=3)
    first_jti = table.all()[0]["jti"]

    password_resets.supersede_user_tokens(user_id=3)
    # The previously-issued (unused) token is now marked used and cannot consume.
    assert password_resets.consume_reset_token(first_jti) is False
