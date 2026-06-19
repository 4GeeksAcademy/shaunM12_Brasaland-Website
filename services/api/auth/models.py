"""Pydantic models for the authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator

from users.models import UserCreate, _validate_password


class RegisterRequest(UserCreate):
    """Registration payload — same shape/validation as creating a user."""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_password(value)


class MessageResponse(BaseModel):
    message: str


__all__ = [
    "RegisterRequest",
    "TokenResponse",
    "VerifyEmailRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "MessageResponse",
]
