"""P24-2 tool tests — incidents, inventory write rejection, scopes."""

from __future__ import annotations

from typing import Any

import pytest

from brasaland_company_tools import errors
from brasaland_company_tools.tools.incidents import (
    IncidentCreatePayload,
    manage_incident_tickets,
)
from brasaland_company_tools.tools.inventory import query_inventory
from mcp.server.auth.provider import AccessToken


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCPAUTH_REGISTRATION_SECRET", "test-registration-secret")
    monkeypatch.setenv("MCP_INTERNAL_API_BASE_URL", "http://127.0.0.1:8000")


def _set_token_scopes(monkeypatch: pytest.MonkeyPatch, scopes: list[str]) -> None:
    token = AccessToken(
        token="test-token",
        client_id="test-client",
        scopes=scopes,
        expires_at=None,
    )

    monkeypatch.setattr(
        "brasaland_company_tools.scopes.get_access_token",
        lambda: token,
    )


def test_manage_incident_get_requires_incident_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_token_scopes(monkeypatch, ["incidents:read"])
    result = manage_incident_tickets(action="get")
    assert result["ok"] is False
    assert result["error_code"] == errors.VALIDATION_ERROR


def test_manage_incident_read_requires_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_token_scopes(monkeypatch, ["incidents:write"])
    result = manage_incident_tickets(action="list")
    assert result["ok"] is False
    assert result["error_code"] == errors.AUTHZ_INSUFFICIENT_SCOPE


def test_manage_incident_list_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_token_scopes(monkeypatch, ["incidents:read"])

    def fake_request(
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any | None, str | None]:
        assert method == "GET"
        assert path == "/incidents"
        assert params == {"category": "supply_issue"}
        return 200, [{"id": 1, "title": "Test"}], None

    monkeypatch.setattr("brasaland_company_tools.tools.incidents.request_json", fake_request)
    from brasaland_company_tools.tools.incidents import IncidentFilters

    result = manage_incident_tickets(
        action="list",
        filters=IncidentFilters(category="supply_issue"),
    )
    assert result["ok"] is True
    assert result["action"] == "list"
    assert len(result["data"]) == 1


def test_manage_incident_create_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_token_scopes(monkeypatch, ["incidents:write"])

    def fake_request(
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any | None, str | None]:
        assert method == "POST"
        assert path == "/incidents"
        assert json_body is not None
        assert json_body["origin"] == "branch"
        return 201, {"id": 99, **json_body}, None

    monkeypatch.setattr("brasaland_company_tools.tools.incidents.request_json", fake_request)
    payload = IncidentCreatePayload(
        title="Oven down",
        description="Main oven offline",
        category="equipment_failure",
        origin="branch",
        branch="miami_doral",
    )
    result = manage_incident_tickets(action="create", payload=payload)
    assert result["ok"] is True
    assert result["data"]["id"] == 99


def test_manage_incident_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_token_scopes(monkeypatch, ["incidents:read"])

    monkeypatch.setattr(
        "brasaland_company_tools.tools.incidents.request_json",
        lambda *args, **kwargs: (200, {"by_status": {"open": 3}}, None),
    )
    result = manage_incident_tickets(action="summary")
    assert result["ok"] is True
    assert result["data"]["by_status"]["open"] == 3


def test_query_inventory_write_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_token_scopes(monkeypatch, ["inventory:read"])
    result = query_inventory(action="create")  # type: ignore[arg-type]
    assert result["ok"] is False
    assert result["error_code"] == errors.INVENTORY_WRITE_FORBIDDEN


def test_query_inventory_restock_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_token_scopes(monkeypatch, ["inventory:read"])
    result = query_inventory(name="restock tomatoes")
    assert result["error_code"] == errors.INVENTORY_WRITE_FORBIDDEN


def test_query_inventory_list_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_token_scopes(monkeypatch, ["inventory:read"])

    def fake_request(
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any | None, str | None]:
        assert path == "/inventory/products"
        return 200, [{"id": 1, "sku": "US-FLOUR-01", "name": "Flour"}], None

    monkeypatch.setattr("brasaland_company_tools.tools.inventory.request_json", fake_request)
    result = query_inventory(sku="FLOUR")
    assert result["ok"] is True
    assert result["count"] == 1


def test_query_inventory_requires_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_token_scopes(monkeypatch, ["incidents:read"])
    result = query_inventory()
    assert result["error_code"] == errors.AUTHZ_INSUFFICIENT_SCOPE
