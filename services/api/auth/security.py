"""Password hashing and JWT encode/decode helpers.

Settings come from ``config.py`` so the signing secret is never hardcoded.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

import config

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt only consumes the first 72 bytes of a password.
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: int | str, expires_minutes: int | None = None) -> str:
    """Sign a JWT whose ``sub`` is the user id (stored as a string per spec)."""
    minutes = (
        expires_minutes
        if expires_minutes is not None
        else config.ACCESS_TOKEN_EXPIRES_MINUTES
    )
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode/validate a JWT, raising ``jose.JWTError`` on any problem."""
    return jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])


# --- Opaque tokens (refresh / email verification) ---------------------------
# These are high-entropy random strings, not JWTs. We store only their SHA-256
# hash so a database leak does not expose usable tokens.


def generate_opaque_token() -> str:
    """Return a new URL-safe random token to hand to the client."""
    return secrets.token_urlsafe(32)


def hash_opaque_token(raw_token: str) -> str:
    """Hash an opaque token for storage/lookup (constant for a given input)."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


__all__ = [
    "JWTError",
    "BCRYPT_MAX_BYTES",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "generate_opaque_token",
    "hash_opaque_token",
]
