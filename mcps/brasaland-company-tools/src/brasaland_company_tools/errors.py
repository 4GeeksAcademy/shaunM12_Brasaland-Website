"""Distinct MCP error codes for auth, authorization, and validation (P24-L16)."""

from __future__ import annotations

from typing import Any

AUTH_MISSING = "AUTH_MISSING"
AUTH_INVALID = "AUTH_INVALID"
AUTHZ_INSUFFICIENT_SCOPE = "AUTHZ_INSUFFICIENT_SCOPE"
VALIDATION_ERROR = "VALIDATION_ERROR"
INVENTORY_WRITE_FORBIDDEN = "INVENTORY_WRITE_FORBIDDEN"
UPSTREAM_NOT_FOUND = "UPSTREAM_NOT_FOUND"
UPSTREAM_ERROR = "UPSTREAM_ERROR"


def error_payload(
    code: str,
    message: str,
    *,
    http_status: int | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "error_code": code,
        "message": message,
    }
    if http_status is not None:
        payload["http_status"] = http_status
    if details:
        payload["details"] = details
    return payload


def auth_missing_message() -> str:
    return "Authorization required. Provide a valid OAuth 2.1 bearer access token."


def auth_invalid_message() -> str:
    return "Access token is invalid or expired."


def authz_insufficient_scope_message(required: str | list[str]) -> str:
    if isinstance(required, str):
        return f"Insufficient scope. Required: {required}"
    joined = ", ".join(required)
    return f"Insufficient scope. Required one of: {joined}"
