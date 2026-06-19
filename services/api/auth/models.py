"""Pydantic models for the authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel

from users.models import UserCreate


class RegisterRequest(UserCreate):
    """Registration payload — same shape/validation as creating a user."""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyEmailRequest(BaseModel):
    token: str


class MessageResponse(BaseModel):
    message: str


__all__ = [
    "RegisterRequest",
    "TokenResponse",
    "VerifyEmailRequest",
    "MessageResponse",
]
