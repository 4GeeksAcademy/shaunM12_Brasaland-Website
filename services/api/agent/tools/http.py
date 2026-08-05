"""Injectable HTTP client for Support Agent tools (P2-L38)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 5.0


def api_base_url() -> str:
    raw = os.getenv("AGENT_INTERNAL_API_BASE_URL", DEFAULT_BASE_URL).strip()
    return raw.rstrip("/") if raw else DEFAULT_BASE_URL


def tool_timeout_seconds() -> float:
    raw = os.getenv("AGENT_TOOL_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    return float(raw)


def fetch_json(
    method: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
) -> tuple[int, Any | None, str | None]:
    """Perform an internal API request. Returns (status_code, json_body, error_reason).

    ``error_reason`` is set for transport failures (``timeout``) or non-JSON bodies.
    """
    url = f"{api_base_url()}{path}"
    if params:
        query = urlencode({k: v for k, v in params.items() if v is not None})
        if query:
            url = f"{url}?{query}"

    request_headers = dict(headers or {})
    effective_timeout = timeout if timeout is not None else tool_timeout_seconds()

    try:
        with httpx.Client(timeout=effective_timeout) as client:
            response = client.request(method.upper(), url, headers=request_headers)
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
