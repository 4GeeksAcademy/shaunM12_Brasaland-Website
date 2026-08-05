"""mcpauth OAuth wiring for FastMCP 3.x (P24-L4 — not FastMCP built-in JWT/OAuth)."""

from __future__ import annotations

from fastmcp.server.auth import RemoteAuthProvider, TokenVerifier
from fastmcp.server.auth.auth import AccessToken
from getmcpauth import McpAuthTokenVerifier
from pydantic import AnyHttpUrl

from . import errors
from .config import (
    mcpauth_introspection_url,
    mcpauth_issuer_url,
    mcpauth_registration_secret,
    resource_server_url,
    scopes_supported,
)

# Re-export for tool scope checks in P24-2
SCOPES_SUPPORTED = scopes_supported()


class McpAuthVerifierAdapter(TokenVerifier):
    """Bridge getmcpauth ``McpAuthTokenVerifier`` to FastMCP ``RemoteAuthProvider``."""

    def __init__(
        self,
        inner: McpAuthTokenVerifier,
        *,
        base_url: str,
        required_scopes: list[str] | None = None,
        resource_base_url: str | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            required_scopes=required_scopes,
            resource_base_url=resource_base_url,
        )
        self._inner = inner

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            verified = await self._inner.verify_token(token)
        except RuntimeError as exc:
            raise RuntimeError(
                f"{errors.AUTH_INVALID}: mcpauth introspection failed — {exc}"
            ) from exc
        if verified is None:
            return None
        return AccessToken(
            token=verified.token,
            client_id=verified.client_id,
            scopes=verified.scopes,
            expires_at=verified.expires_at,
            subject=getattr(verified, "subject", None),
        )


def build_auth_provider() -> RemoteAuthProvider:
    """Create OAuth resource-server auth for this MCP server."""
    secret = mcpauth_registration_secret()
    issuer = mcpauth_issuer_url()
    resource_url = resource_server_url()
    introspect = mcpauth_introspection_url()

    inner = McpAuthTokenVerifier(
        introspect,
        registration_secret=secret,
    )
    adapter = McpAuthVerifierAdapter(
        inner,
        base_url=resource_url,
        resource_base_url=resource_url,
        required_scopes=None,
    )
    return RemoteAuthProvider(
        token_verifier=adapter,
        authorization_servers=[AnyHttpUrl(issuer)],
        base_url=resource_url,
        resource_base_url=resource_url,
        scopes_supported=SCOPES_SUPPORTED,
        resource_name="brasaland-company-tools",
    )
