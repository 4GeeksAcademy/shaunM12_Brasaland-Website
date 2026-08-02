"""P24-1 auth tests — OAuth required for MCP tool discovery."""

from __future__ import annotations

import os

import httpx
import pytest

from brasaland_company_tools.auth import build_auth_provider
from brasaland_company_tools.config import mcpauth_registration_secret


@pytest.fixture(autouse=True)
def _set_mcpauth_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCPAUTH_REGISTRATION_SECRET", "test-registration-secret")
    monkeypatch.setenv("MCP_SERVER_PORT", "8765")
    monkeypatch.setenv("MCP_RESOURCE_SERVER_URL", "http://127.0.0.1:8765")


def test_build_auth_provider_requires_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCPAUTH_REGISTRATION_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="MCPAUTH_REGISTRATION_SECRET"):
        mcpauth_registration_secret()


def test_build_auth_provider_ok() -> None:
    provider = build_auth_provider()
    assert provider.resource_name == "brasaland-company-tools"


@pytest.mark.asyncio
async def test_unauthenticated_tools_list_returns_401() -> None:
    os.environ.setdefault("MCPAUTH_REGISTRATION_SECRET", "test-registration-secret")
    from brasaland_company_tools.server import create_mcp

    mcp = create_mcp()
    app = mcp.http_app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.text == "OK"

        metadata = await client.get("/.well-known/oauth-protected-resource/mcp")
        assert metadata.status_code == 200
        body = metadata.json()
        assert body["resource"] == "http://127.0.0.1:8765/mcp"
        assert "incidents:read" in body["scopes_supported"]

        response = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        assert response.status_code == 401
