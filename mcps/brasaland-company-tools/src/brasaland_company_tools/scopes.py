"""OAuth scope checks for MCP tools (P24-L12)."""

from __future__ import annotations

from mcp.server.auth.middleware.auth_context import get_access_token

from . import errors


def _token_scopes() -> set[str]:
    token = get_access_token()
    if token is None:
        return set()
    return set(token.scopes or [])


def has_scope(scope: str) -> bool:
    return scope in _token_scopes()


def require_scope(scope: str) -> dict | None:
    if has_scope(scope):
        return None
    return errors.error_payload(
        errors.AUTHZ_INSUFFICIENT_SCOPE,
        errors.authz_insufficient_scope_message(scope),
    )


def require_any_scope(scopes: list[str]) -> dict | None:
    held = _token_scopes()
    if any(scope in held for scope in scopes):
        return None
    return errors.error_payload(
        errors.AUTHZ_INSUFFICIENT_SCOPE,
        errors.authz_insufficient_scope_message(scopes),
    )
