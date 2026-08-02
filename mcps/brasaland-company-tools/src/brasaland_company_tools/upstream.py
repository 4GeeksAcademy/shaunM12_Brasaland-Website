"""HTTP client for bare FastAPI mounts (P24-L3)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

import httpx

from . import errors
from .config import internal_api_base_url
from .upstream_auth import UPSTREAM_AUTH_HEADER, get_upstream_authorization

DEFAULT_TIMEOUT_SECONDS = 5.0


def tool_timeout_seconds() -> float:
    raw = os.getenv("MCP_TOOL_TIMEOUT_SECONDS", "").strip()
    if raw:
        return float(raw)
    return DEFAULT_TIMEOUT_SECONDS


def _build_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = dict(extra or {})
    upstream_auth = get_upstream_authorization()
    if upstream_auth:
        headers["Authorization"] = upstream_auth
    return headers


def request_json(
    method: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any | None, str | None]:
    """Call FastAPI and return ``(status_code, json_body, transport_error)``."""
    base = internal_api_base_url()
    url = f"{base}{path}"
    if params:
        query = urlencode({key: value for key, value in params.items() if value is not None})
        if query:
            url = f"{url}?{query}"

    merged_headers = _build_headers(headers)
    timeout = tool_timeout_seconds()

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method.upper(),
                url,
                headers=merged_headers,
                json=json_body,
            )
    except httpx.TimeoutException:
        return 0, None, "timeout"
    except httpx.HTTPError:
        return 0, None, "http_error"

    if response.status_code == 204 or not response.content:
        return response.status_code, None, None

    try:
        return response.status_code, response.json(), None
    except ValueError:
        return response.status_code, None, "invalid_json"


def map_upstream_failure(
    *,
    status: int,
    body: Any | None,
    transport_error: str | None,
    action: str,
) -> dict[str, Any]:
    if transport_error == "timeout":
        return errors.error_payload(
            errors.UPSTREAM_ERROR,
            "Upstream API request timed out.",
            details={"action": action, "reason": "timeout"},
        )
    if transport_error is not None:
        return errors.error_payload(
            errors.UPSTREAM_ERROR,
            "Upstream API request failed.",
            http_status=status or None,
            details={"action": action, "reason": transport_error},
        )
    if status == 401:
        return errors.error_payload(
            errors.AUTH_MISSING,
            "Upstream API rejected the request. Provide a Brasaland JWT via "
            f"{UPSTREAM_AUTH_HEADER} (support agent) or ensure the caller is authorized.",
            http_status=401,
            details={"action": action},
        )
    if status == 404:
        message = "Resource not found."
        if isinstance(body, dict) and body.get("detail"):
            message = str(body["detail"])
        return errors.error_payload(
            errors.UPSTREAM_NOT_FOUND,
            message,
            http_status=404,
            details={"action": action},
        )
    if status == 400 or status == 422:
        detail = body
        if isinstance(body, dict):
            detail = body.get("detail", body)
        return errors.error_payload(
            errors.VALIDATION_ERROR,
            "Upstream validation failed.",
            http_status=status,
            details={"action": action, "upstream": detail},
        )
    if status >= 500:
        return errors.error_payload(
            errors.UPSTREAM_ERROR,
            "Upstream API returned a server error.",
            http_status=status,
            details={"action": action},
        )
    return errors.error_payload(
        errors.UPSTREAM_ERROR,
        f"Unexpected upstream response (HTTP {status}).",
        http_status=status,
        details={"action": action, "upstream": body},
    )
