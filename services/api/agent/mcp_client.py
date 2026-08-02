"""MCP client for Support Agent incident reads and writes (P24-3, P24-3b)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import httpx

from auth.security import JWTError, decode_access_token
from incidents.constants import STATUS_TRANSITIONS
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

INCIDENTS_SOURCE = "incidents_api"
_READ_SCOPES = ["incidents:read"]
_WRITE_SCOPES = ["incidents:read", "incidents:write"]

_cached_client_id: str | None = None


def mcp_endpoint_url() -> str:
    raw = os.getenv("AGENT_MCP_SERVER_URL", "http://127.0.0.1:8765").strip().rstrip("/")
    if raw.endswith("/mcp"):
        return raw
    return f"{raw}/mcp"


def mcpauth_issuer_url() -> str:
    raw = os.getenv("MCPAUTH_ISSUER_URL", "https://getmcpauth.dev").strip()
    return raw.rstrip("/") if raw else "https://getmcpauth.dev"


def mcpauth_registration_secret() -> str:
    secret = os.getenv("MCPAUTH_REGISTRATION_SECRET", "").strip()
    if not secret:
        raise RuntimeError("MCPAUTH_REGISTRATION_SECRET is required for agent MCP calls.")
    return secret


def _normalize_row(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "description": raw.get("description"),
        "status": raw.get("status"),
        "origin": raw.get("origin"),
        "branch": raw.get("branch"),
        "category": raw.get("category"),
    }


def _failure_envelope(
    *,
    http_status: int,
    reason: str,
    error: str | None = None,
    incident_id: int | None = None,
    filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "source": INCIDENTS_SOURCE,
        "ok": False,
        "http_status": http_status,
        "rows": [],
        "error": error or reason,
        "reason": reason,
    }
    if incident_id is not None:
        envelope["incident_id"] = incident_id
    if filters:
        envelope["filters"] = filters
    return envelope


def _subject_from_auth_header(auth_header: str | None) -> str:
    if not auth_header:
        return "support-agent-anonymous"
    token = auth_header.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is not None:
            return str(sub)
    except (JWTError, ValueError):
        logger.warning("Could not decode caller JWT for MCP subject; using anonymous subject.")
    return "support-agent-anonymous"


def _ensure_mcp_client_id() -> str:
    global _cached_client_id
    configured = os.getenv("AGENT_MCP_CLIENT_ID", "").strip()
    if configured:
        return configured
    if _cached_client_id:
        return _cached_client_id

    issuer = mcpauth_issuer_url()
    secret = mcpauth_registration_secret()
    payload = {
        "client_name": "brasaland-support-agent",
        "redirect_uris": ["http://127.0.0.1/oauth/callback"],
        "token_endpoint_auth_method": "none",
    }
    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            f"{issuer}/api/oauth/register",
            headers={"Authorization": f"Bearer {secret}"},
            json=payload,
        )
        response.raise_for_status()
        body = response.json()
    client_id = str(body.get("client_id", "")).strip()
    if not client_id:
        raise RuntimeError("getmcpauth client registration did not return client_id.")
    _cached_client_id = client_id
    return client_id


def mint_mcp_access_token(*, subject: str, scopes: list[str]) -> str:
    """Mint a server-to-server MCP OAuth token (P24-L10)."""
    issuer = mcpauth_issuer_url()
    secret = mcpauth_registration_secret()
    client_id = _ensure_mcp_client_id()
    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            f"{issuer}/api/oauth/token/exchange",
            headers={"Authorization": f"Bearer {secret}"},
            json={
                "client_id": client_id,
                "subject": subject,
                "scopes": scopes,
            },
        )
        response.raise_for_status()
        body = response.json()
    token = body.get("access_token")
    if not token:
        raise RuntimeError("getmcpauth token exchange did not return access_token.")
    return str(token)


def _unwrap_tool_payload(raw: Any) -> Any:
    """Normalize LangChain / MCP SDK tool outputs to a dict or JSON string."""
    if raw is None:
        return raw

    content = getattr(raw, "content", None)
    if content is not None and content is not raw:
        return _unwrap_tool_payload(content)

    if isinstance(raw, dict):
        if raw.get("type") == "text" and "text" in raw:
            return _unwrap_tool_payload(raw["text"])
        return raw

    if isinstance(raw, list):
        if not raw:
            return raw
        text_parts: list[str] = []
        for item in raw:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                text_parts.append(item)
            else:
                nested = _unwrap_tool_payload(item)
                if isinstance(nested, dict):
                    return nested
        if text_parts:
            combined = text_parts[0] if len(text_parts) == 1 else "".join(text_parts)
            return _unwrap_tool_payload(combined)
        return _unwrap_tool_payload(raw[0])

    return raw


def _parse_tool_result(raw: Any) -> dict[str, Any]:
    payload = _unwrap_tool_payload(raw)
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"ok": False, "error_code": "UPSTREAM_ERROR", "message": payload}
    return {"ok": False, "error_code": "UPSTREAM_ERROR", "message": "Invalid MCP tool response."}


def _mcp_error_to_envelope(
    mcp_result: dict[str, Any],
    *,
    incident_id: int | None,
    filters: dict[str, str],
) -> dict[str, Any]:
    code = str(mcp_result.get("error_code", "UPSTREAM_ERROR"))
    http_status = int(mcp_result.get("http_status") or 502)
    details = mcp_result.get("details") or {}
    upstream = details.get("upstream")
    upstream_text = str(upstream).lower() if upstream is not None else ""
    if code == "VALIDATION_ERROR" and "invalid status transition" in upstream_text:
        return _failure_envelope(
            http_status=422,
            reason="invalid_status_transition",
            incident_id=incident_id,
            filters=filters,
            error=str(upstream),
        )
    if code == "UPSTREAM_NOT_FOUND":
        return _failure_envelope(
            http_status=404,
            reason="not_found",
            incident_id=incident_id,
            filters=filters,
        )
    if code == "AUTH_MISSING":
        return _failure_envelope(
            http_status=401,
            reason="http_401",
            incident_id=incident_id,
            filters=filters,
            error=mcp_result.get("message"),
        )
    if code == "VALIDATION_ERROR":
        return _failure_envelope(
            http_status=422,
            reason="http_422",
            incident_id=incident_id,
            filters=filters,
            error=mcp_result.get("message"),
        )
    return _failure_envelope(
        http_status=http_status,
        reason=f"http_{http_status}" if http_status else "http_error",
        incident_id=incident_id,
        filters=filters,
        error=mcp_result.get("message"),
    )


def _success_envelope_from_mcp(
    mcp_result: dict[str, Any],
    *,
    incident_id: int | None,
    filters: dict[str, str],
    action: str = "list",
) -> dict[str, Any]:
    data = mcp_result.get("data")
    mcp_action = str(mcp_result.get("action") or action)

    if mcp_action == "summary":
        if not isinstance(data, dict):
            return _failure_envelope(
                http_status=502,
                reason="invalid_response",
                filters=filters,
            )
        return {
            "source": INCIDENTS_SOURCE,
            "ok": True,
            "http_status": 200,
            "filters": filters,
            "rows": [],
            "summary": data,
            "action": "summary",
            "error": None,
            "reason": None,
        }

    if incident_id is not None:
        if not isinstance(data, dict):
            return _failure_envelope(
                http_status=502,
                reason="invalid_response",
                incident_id=incident_id,
                filters=filters,
            )
        return {
            "source": INCIDENTS_SOURCE,
            "ok": True,
            "http_status": 200,
            "incident_id": incident_id,
            "filters": filters,
            "rows": [_normalize_row(data)],
            "error": None,
            "reason": None,
        }

    if not isinstance(data, list):
        return _failure_envelope(
            http_status=502,
            reason="invalid_response",
            filters=filters,
        )
    rows = [_normalize_row(item) for item in data if isinstance(item, dict)]
    if not rows:
        return {
            "source": INCIDENTS_SOURCE,
            "ok": True,
            "http_status": 200,
            "filters": filters,
            "rows": [],
            "error": None,
            "reason": "empty",
        }
    return {
        "source": INCIDENTS_SOURCE,
        "ok": True,
        "http_status": 200,
        "filters": filters,
        "rows": rows,
        "action": mcp_action,
        "error": None,
        "reason": None,
    }


def _success_envelope_from_write(
    mcp_result: dict[str, Any],
    *,
    write_action: str,
) -> dict[str, Any]:
    data = mcp_result.get("data")
    if not isinstance(data, dict):
        return _failure_envelope(
            http_status=502,
            reason="invalid_response",
        )
    return {
        "source": INCIDENTS_SOURCE,
        "ok": True,
        "http_status": 200,
        "rows": [_normalize_row(data)],
        "action": write_action,
        "error": None,
        "reason": None,
    }


async def _call_manage_incident_tickets_async(
    *,
    arguments: dict[str, Any],
    mcp_token: str,
    upstream_auth_header: str | None,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {mcp_token}"}
    if upstream_auth_header:
        headers["X-Upstream-Authorization"] = upstream_auth_header

    client = MultiServerMCPClient(
        {
            "brasaland-company-tools": {
                "transport": "http",
                "url": mcp_endpoint_url(),
                "headers": headers,
            }
        }
    )
    tools = await client.get_tools()
    tool = next((item for item in tools if item.name == "manage_incident_tickets"), None)
    if tool is None:
        return {
            "ok": False,
            "error_code": "UPSTREAM_ERROR",
            "message": "manage_incident_tickets not found on MCP server.",
        }
    raw = await tool.ainvoke(arguments)
    return _parse_tool_result(raw)


def lookup_incidents_via_mcp(
    *,
    incident_id: int | None,
    filters: dict[str, str] | None,
    auth_header: str | None,
    incident_action: str = "list",
) -> dict[str, Any]:
    """Call MCP ``manage_incident_tickets`` and return a P2-L36 envelope."""
    filter_copy = dict(filters or {})
    subject = _subject_from_auth_header(auth_header)
    action = incident_action if incident_action in {"list", "get", "summary"} else "list"

    try:
        mcp_token = mint_mcp_access_token(subject=subject, scopes=_READ_SCOPES)
    except Exception as exc:
        logger.warning("MCP token mint failed: %s", exc)
        return _failure_envelope(
            http_status=0,
            reason="http_error",
            incident_id=incident_id,
            filters=filter_copy,
            error="mcp_token_mint_failed",
        )

    if action == "summary":
        arguments: dict[str, Any] = {"action": "summary"}
    elif incident_id is not None:
        arguments = {"action": "get", "incident_id": incident_id}
    else:
        arguments = {"action": "list"}
        if filter_copy:
            arguments["filters"] = filter_copy

    try:
        mcp_result = asyncio.run(
            _call_manage_incident_tickets_async(
                arguments=arguments,
                mcp_token=mcp_token,
                upstream_auth_header=auth_header,
            )
        )
    except httpx.TimeoutException:
        return _failure_envelope(
            http_status=0,
            reason="timeout",
            incident_id=incident_id,
            filters=filter_copy,
        )
    except Exception as exc:
        logger.warning("MCP incident lookup failed: %s", exc)
        return _failure_envelope(
            http_status=0,
            reason="http_error",
            incident_id=incident_id,
            filters=filter_copy,
        )

    if not mcp_result.get("ok"):
        return _mcp_error_to_envelope(
            mcp_result,
            incident_id=incident_id,
            filters=filter_copy,
        )
    return _success_envelope_from_mcp(
        mcp_result,
        incident_id=incident_id,
        filters=filter_copy,
        action=action,
    )


def mutate_incident_via_mcp(
    *,
    write_action: str,
    auth_header: str | None,
    incident_id: int | None = None,
    write_status: str | None = None,
    write_payload: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Call MCP ``manage_incident_tickets`` for create or update_status."""
    subject = _subject_from_auth_header(auth_header)

    try:
        mcp_token = mint_mcp_access_token(subject=subject, scopes=_WRITE_SCOPES)
    except Exception as exc:
        logger.warning("MCP token mint failed: %s", exc)
        return _failure_envelope(
            http_status=0,
            reason="http_error",
            incident_id=incident_id,
            error="mcp_token_mint_failed",
        )

    if write_action == "create":
        if not write_payload:
            return _failure_envelope(
                http_status=422,
                reason="http_422",
                error="missing_create_payload",
            )
        arguments: dict[str, Any] = {
            "action": "create",
            "payload": write_payload,
        }
    elif write_action == "update_status":
        if incident_id is None or not write_status:
            return _failure_envelope(
                http_status=422,
                reason="http_422",
                incident_id=incident_id,
                error="missing_update_fields",
            )
        try:
            return _mutate_update_status_via_mcp(
                incident_id=incident_id,
                write_status=write_status,
                mcp_token=mcp_token,
                upstream_auth_header=auth_header,
            )
        except httpx.TimeoutException:
            return _failure_envelope(
                http_status=0,
                reason="timeout",
                incident_id=incident_id,
            )
        except Exception as exc:
            logger.warning("MCP incident status update failed: %s", exc)
            return _failure_envelope(
                http_status=0,
                reason="http_error",
                incident_id=incident_id,
            )
    else:
        return _failure_envelope(
            http_status=422,
            reason="http_422",
            error=f"unsupported_write_action:{write_action}",
        )

    try:
        mcp_result = asyncio.run(
            _call_manage_incident_tickets_async(
                arguments=arguments,
                mcp_token=mcp_token,
                upstream_auth_header=auth_header,
            )
        )
    except httpx.TimeoutException:
        return _failure_envelope(
            http_status=0,
            reason="timeout",
            incident_id=incident_id,
        )
    except Exception as exc:
        logger.warning("MCP incident mutate failed: %s", exc)
        return _failure_envelope(
            http_status=0,
            reason="http_error",
            incident_id=incident_id,
        )

    if not mcp_result.get("ok"):
        return _mcp_error_to_envelope(
            mcp_result,
            incident_id=incident_id,
            filters={},
        )
    return _success_envelope_from_write(mcp_result, write_action=write_action)


def _status_update_steps(current_status: str, target_status: str) -> list[str] | None:
    """Return ordered status updates to reach *target_status*, or None if impossible."""
    if current_status == target_status:
        return []
    if target_status == "resolved" and current_status == "open":
        return ["in_progress", "resolved"]
    allowed = STATUS_TRANSITIONS.get(current_status, ())
    if target_status in allowed:
        return [target_status]
    return None


def _invoke_mcp_tool(
    *,
    arguments: dict[str, Any],
    mcp_token: str,
    upstream_auth_header: str | None,
) -> dict[str, Any]:
    return asyncio.run(
        _call_manage_incident_tickets_async(
            arguments=arguments,
            mcp_token=mcp_token,
            upstream_auth_header=upstream_auth_header,
        )
    )


def _mutate_update_status_via_mcp(
    *,
    incident_id: int,
    write_status: str,
    mcp_token: str,
    upstream_auth_header: str | None,
) -> dict[str, Any]:
    """Update incident status, chaining open → in_progress → resolved when needed."""
    get_result = _invoke_mcp_tool(
        arguments={"action": "get", "incident_id": incident_id},
        mcp_token=mcp_token,
        upstream_auth_header=upstream_auth_header,
    )
    if not get_result.get("ok"):
        return _mcp_error_to_envelope(
            get_result,
            incident_id=incident_id,
            filters={},
        )

    data = get_result.get("data")
    if not isinstance(data, dict):
        return _failure_envelope(
            http_status=502,
            reason="invalid_response",
            incident_id=incident_id,
        )

    current_status = str(data.get("status") or "")
    steps = _status_update_steps(current_status, write_status)
    if steps is None:
        return _failure_envelope(
            http_status=422,
            reason="invalid_status_transition",
            incident_id=incident_id,
            error=f"Cannot change incident {incident_id} from {current_status} to {write_status}.",
        )

    if not steps:
        return _success_envelope_from_write(
            {"ok": True, "action": "update_status", "data": data},
            write_action="update_status",
        )

    last_result: dict[str, Any] | None = None
    for step_status in steps:
        last_result = _invoke_mcp_tool(
            arguments={
                "action": "update_status",
                "incident_id": incident_id,
                "status": step_status,
            },
            mcp_token=mcp_token,
            upstream_auth_header=upstream_auth_header,
        )
        if not last_result.get("ok"):
            return _mcp_error_to_envelope(
                last_result,
                incident_id=incident_id,
                filters={},
            )

    assert last_result is not None
    return _success_envelope_from_write(last_result, write_action="update_status")
