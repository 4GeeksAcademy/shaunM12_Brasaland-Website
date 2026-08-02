"""Resolve Brasaland JWT for upstream FastAPI calls (P24-L11)."""

from __future__ import annotations

UPSTREAM_AUTH_HEADER = "X-Upstream-Authorization"


def get_upstream_authorization() -> str | None:
    """Return the caller JWT to forward to FastAPI as ``Authorization``.

    MCP OAuth uses the standard ``Authorization`` header. The support agent (P24-3)
    passes the user's Brasaland JWT via ``X-Upstream-Authorization`` instead.
    """
    try:
        from fastmcp.server.dependencies import get_http_request

        request = get_http_request()
        upstream = request.headers.get(UPSTREAM_AUTH_HEADER)
        if upstream and upstream.strip():
            value = upstream.strip()
            return value if value.lower().startswith("bearer ") else f"Bearer {value}"
    except Exception:
        return None
    return None
