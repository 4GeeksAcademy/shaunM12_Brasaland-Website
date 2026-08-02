"""FastMCP HTTP server entrypoint (P24-0 scaffold, P24-1 OAuth, P24-2 tools)."""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from .auth import build_auth_provider
from .config import server_host, server_port
from .logging_tools import ToolInvocationLoggingMiddleware
from .tools.incidents import IncidentCreatePayload, IncidentFilters, manage_incident_tickets
from .tools.inventory import query_inventory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_mcp() -> FastMCP:
    auth = build_auth_provider()
    mcp = FastMCP(
        "brasaland-company-tools",
        instructions=(
            "Brasaland operational MCP server. Exposes incident ticket management "
            "(create, update status, query, summary) and read-only inventory queries. "
            "All MCP tools require OAuth 2.1 bearer tokens issued via getmcpauth. "
            "Scopes: incidents:read, incidents:write, inventory:read. "
            "Upstream FastAPI calls require a Brasaland JWT via X-Upstream-Authorization "
            "when using the support agent; external OAuth clients need the same header "
            "to call protected /incidents endpoints."
        ),
        auth=auth,
        middleware=[ToolInvocationLoggingMiddleware()],
    )

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(_request: Request) -> PlainTextResponse:
        """Liveness probe — unauthenticated (not an MCP tool)."""
        return PlainTextResponse("OK")

    @mcp.custom_route("/auth/errors", methods=["GET"])
    async def auth_error_reference(_request: Request) -> JSONResponse:
        """Document distinct auth error codes for external MCP clients (P24-L16)."""
        return JSONResponse(
            {
                "codes": {
                    "AUTH_MISSING": "No Authorization bearer token on MCP request",
                    "AUTH_INVALID": "Token failed mcpauth introspection",
                    "AUTHZ_INSUFFICIENT_SCOPE": "Valid token missing required scope",
                    "VALIDATION_ERROR": "Invalid tool input or upstream validation",
                    "INVENTORY_WRITE_FORBIDDEN": "Inventory write attempt on read-only tool",
                    "UPSTREAM_NOT_FOUND": "FastAPI resource not found",
                    "UPSTREAM_ERROR": "FastAPI transport or server error",
                }
            }
        )

    @mcp.tool
    def server_status() -> dict[str, str]:
        """Report MCP server identity and phase. Requires valid OAuth bearer token."""
        return {
            "server": "brasaland-company-tools",
            "phase": "P24-2",
            "transport": "streamable-http",
            "oauth": "getmcpauth.dev",
            "tools": "manage_incident_tickets, query_inventory",
        }

    @mcp.tool(name="manage_incident_tickets")
    def manage_incident_tickets_tool(
        action: str,
        incident_id: int | None = None,
        status: str | None = None,
        filters: IncidentFilters | None = None,
        payload: IncidentCreatePayload | None = None,
    ) -> dict:
        """Create, update status, query, or summarize Brasaland incident tickets.

        Read actions (get, list, summary) require scope incidents:read.
        Write actions (create, update_status) require incidents:write.
        Status updates follow API lifecycle rules: open → in_progress → resolved | discarded.
        Use field ``origin`` (never ``source``). List supports filters.status, origin, branch, category.
        """
        return manage_incident_tickets(
            action=action,  # type: ignore[arg-type]
            incident_id=incident_id,
            status=status,
            filters=filters,
            payload=payload,
        )

    @mcp.tool(name="query_inventory")
    def query_inventory_tool(
        action: str = "query",
        product_id: int | None = None,
        sku: str | None = None,
        location_id: int | None = None,
        name: str | None = None,
    ) -> dict:
        """Read-only inventory queries (products, stock, thresholds).

        Requires scope inventory:read. Cannot create products, adjust stock, or submit orders.
        Any write signal returns INVENTORY_WRITE_FORBIDDEN. Upstream: GET /inventory/products only.
        """
        return query_inventory(
            action=action,  # type: ignore[arg-type]
            product_id=product_id,
            sku=sku,
            location_id=location_id,
            name=name,
        )

    return mcp


def run() -> None:
    mcp = create_mcp()
    mcp.run(
        transport="streamable-http",
        host=server_host(),
        port=server_port(),
    )
