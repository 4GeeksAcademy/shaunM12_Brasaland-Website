"""Pure-function unit tests for ``auth/security.py``.

No HTTP, no database — these import the crypto helpers directly and assert on
what they *decide*. This is where the brief's core questions are answered:
does a token get generated correctly? is an expired token rejected? what
happens with an empty / oversized password?
"""

from __future__ import annotations

import pytest

import config
from auth.security import (
    BCRYPT_MAX_BYTES,
    PASSWORD_RESET_TOKEN_TYPE,
    JWTError,
    create_access_token,
    create_password_reset_token,
    decode_access_token,
    decode_password_reset_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)


# --- Password hashing --------------------------------------------------------


def test_hash_password_does_not_return_plaintext():
    hashed = hash_password("supersecret")
    assert hashed != "supersecret"
    assert hashed.startswith("$2")  # bcrypt identifier


def test_verify_password_accepts_correct_and_rejects_wrong():
    hashed = hash_password("supersecret")
    assert verify_password("supersecret", hashed) is True
    assert verify_password("not-the-password", hashed) is False


def test_verify_password_rejects_empty_password():
    """An empty password must never verify against a real hash."""
    hashed = hash_password("supersecret")
    assert verify_password("", hashed) is False


def test_hash_password_is_salted_each_call():
    """Two hashes of the same input differ (random salt) but both verify."""
    first = hash_password("supersecret")
    second = hash_password("supersecret")
    assert first != second
    assert verify_password("supersecret", first)
    assert verify_password("supersecret", second)


def test_password_at_bcrypt_byte_boundary_roundtrips():
    """bcrypt only consumes the first 72 bytes; a 72-byte password still works.

    Documents the truncation boundary that the model validator guards against.
    """
    password = "a" * BCRYPT_MAX_BYTES
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


# --- Access-token generation & validation ------------------------------------


def test_create_access_token_roundtrips_subject():
    token = create_access_token(42)
    claims = decode_access_token(token)
    # ``sub`` is stored as a string per the auth spec.
    assert claims["sub"] == "42"
    assert "exp" in claims


def test_expired_access_token_is_rejected():
    """A token minted with a negative lifetime must fail to decode."""
    token = create_access_token(1, expires_minutes=-1)
    with pytest.raises(JWTError):
        decode_access_token(token)


def test_token_signed_with_wrong_secret_is_rejected(monkeypatch: pytest.MonkeyPatch):
    token = create_access_token(7)
    monkeypatch.setattr(config, "JWT_SECRET_KEY", "a-different-secret")
    with pytest.raises(JWTError):
        decode_access_token(token)


def test_tampered_token_is_rejected():
    token = create_access_token(7)
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    with pytest.raises(JWTError):
        decode_access_token(tampered)


# --- Password-reset tokens (signed JWT carrying type + jti) -------------------


def test_password_reset_token_carries_type_and_jti():
    token = create_password_reset_token(user_id=5, jti="abc123")
    claims = decode_password_reset_token(token)
    assert claims["sub"] == "5"
    assert claims["type"] == PASSWORD_RESET_TOKEN_TYPE
    assert claims["jti"] == "abc123"


def test_expired_password_reset_token_is_rejected():
    token = create_password_reset_token(user_id=5, jti="abc123", expires_minutes=-1)
    with pytest.raises(JWTError):
        decode_password_reset_token(token)


# --- Opaque tokens (refresh / email verification) ----------------------------


def test_generate_opaque_token_is_unique():
    tokens = {generate_opaque_token() for _ in range(100)}
    assert len(tokens) == 100


def test_hash_opaque_token_is_deterministic_and_not_reversible():
    raw = generate_opaque_token()
    assert hash_opaque_token(raw) == hash_opaque_token(raw)
    assert hash_opaque_token(raw) != raw
    # Different inputs hash differently.
    assert hash_opaque_token(raw) != hash_opaque_token(generate_opaque_token())
