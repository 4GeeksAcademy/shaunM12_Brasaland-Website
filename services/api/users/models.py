"""Pydantic models for user management requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

# bcrypt silently ignores bytes past position 72; reject overly long passwords
# up front so behaviour is predictable.
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72


def _validate_password(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long"
        )
    if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError(
            f"Password must be at most {PASSWORD_MAX_BYTES} bytes long"
        )
    return value


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password(value)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_password(value)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_admin: bool
    created_at: datetime


class UserInDB(BaseModel):
    """Full stored representation of a user, including the password hash.

    This is the internal/database model. It must never be used as a response
    model — `hashed_password` is kept out of `UserResponse` so it is never
    returned by the API.
    """

    id: int
    email: EmailStr
    hashed_password: str
    is_active: bool
    is_admin: bool
    created_at: datetime


__all__ = [
    "PASSWORD_MIN_LENGTH",
    "PASSWORD_MAX_BYTES",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
]
