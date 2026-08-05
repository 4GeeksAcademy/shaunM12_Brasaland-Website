"""Structured logging for MCP tool invocations (P24-L17)."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

logger = logging.getLogger("brasaland_mcp.tools")


def _client_label(context: MiddlewareContext[Any]) -> str:
    try:
        from mcp.server.auth.middleware.auth_context import auth_context_var

        auth = auth_context_var.get()
        if auth is None:
            return "anonymous"
        parts: list[str] = []
        if getattr(auth, "subject", None):
            parts.append(f"sub:{auth.subject}")
        elif getattr(auth, "client_id", None):
            parts.append(f"client:{auth.client_id}")
        else:
            parts.append("authenticated")
        scopes = getattr(auth, "scopes", None) or []
        if scopes:
            parts.append(f"scopes:{','.join(scopes)}")
        return "|".join(parts)
    except Exception:
        return "unknown"


def log_tool_event(
    *,
    tool: str,
    client: str,
    result: str,
    **fields: Any,
) -> None:
    extras = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    suffix = f" {extras}" if extras else ""
    logger.info("tool=%s client=%s result=%s%s", tool, client, result, suffix)


class ToolInvocationLoggingMiddleware(Middleware):
    """Emit one log line per tools/list and tools/call (P24-L17)."""

    async def on_list_tools(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        client = _client_label(context)
        try:
            result = await call_next(context)
            log_tool_event(tool="tools/list", client=client, result="ok")
            return result
        except Exception as exc:
            log_tool_event(
                tool="tools/list",
                client=client,
                result="fail",
                error=type(exc).__name__,
            )
            raise

    async def on_call_tool(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        client = _client_label(context)
        tool_name = None
        if context.message is not None:
            params = getattr(context.message, "params", None)
            tool_name = getattr(params, "name", None)
        label = tool_name or "unknown"
        try:
            result = await call_next(context)
            log_tool_event(tool=label, client=client, result="ok")
            return result
        except Exception as exc:
            log_tool_event(
                tool=label,
                client=client,
                result="fail",
                error=type(exc).__name__,
            )
            raise
