"""Environment configuration for the Brasaland company-tools MCP server (P24-L1, P24-L2)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    """Load repo-root ``.env`` if present (works when cwd is ``mcps/brasaland-company-tools``)."""
    here = Path(__file__).resolve()
    for root in [Path.cwd(), here.parent, *here.parents]:
        candidate = root / ".env"
        if candidate.is_file():
            load_dotenv(candidate)
            return
    load_dotenv()


_load_env()


def server_host() -> str:
    raw = os.getenv("MCP_SERVER_HOST", "0.0.0.0").strip()
    return raw or "0.0.0.0"


def server_port() -> int:
    raw = os.getenv("MCP_SERVER_PORT", "8765").strip()
    return int(raw) if raw else 8765


def internal_api_base_url() -> str:
    raw = os.getenv("MCP_INTERNAL_API_BASE_URL", "http://127.0.0.1:8000").strip()
    return raw.rstrip("/") if raw else "http://127.0.0.1:8000"


def mcpauth_issuer_url() -> str:
    raw = os.getenv("MCPAUTH_ISSUER_URL", "https://getmcpauth.dev").strip()
    return raw.rstrip("/") if raw else "https://getmcpauth.dev"


def mcpauth_introspection_url() -> str:
    explicit = os.getenv("MCPAUTH_INTROSPECTION_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    return f"{mcpauth_issuer_url()}/api/oauth/introspect"


def mcpauth_registration_secret() -> str:
    raw = os.getenv("MCPAUTH_REGISTRATION_SECRET", "").strip()
    if not raw:
        raise RuntimeError(
            "MCPAUTH_REGISTRATION_SECRET is required for P24-1 OAuth.\n"
            "1. Create a project at https://getmcpauth.dev/dashboard\n"
            "2. Copy the registration secret from the project page\n"
            "3. Either export it in your shell:\n"
            '     export MCPAUTH_REGISTRATION_SECRET="your-secret-here"\n'
            "   Or add it to the repository root .env file (copy from .env.example):\n"
            "     MCPAUTH_REGISTRATION_SECRET=your-secret-here\n"
            "4. Restart: uv run brasaland-company-tools"
        )
    return raw


def resource_server_url() -> str:
    host = server_host()
    port = server_port()
    raw = os.getenv("MCP_RESOURCE_SERVER_URL", "").strip()
    if raw:
        return raw.rstrip("/")
    if host in {"0.0.0.0", "::"}:
        return f"http://127.0.0.1:{port}"
    return f"http://{host}:{port}"


def scopes_supported() -> list[str]:
    raw = os.getenv("MCP_SCOPES_SUPPORTED", "").strip()
    if raw:
        return [part.strip() for part in raw.split(",") if part.strip()]
    return [
        "incidents:read",
        "incidents:write",
        "inventory:read",
    ]
