"""Unit tests for MCP incident lookup client (P24-3)."""

from __future__ import annotations

import json

import pytest

from agent import mcp_client as mcp_mod


def _sample_incident(incident_id: int = 1) -> dict:
    return {
        "id": incident_id,
        "title": "Oven fault",
        "description": "Main oven not heating",
        "status": "open",
        "origin": "branch",
        "branch": "miami_doral",
        "category": "equipment_failure",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }


def _patch_mcp_call(monkeypatch: pytest.MonkeyPatch, result: dict) -> None:
    async def _fake_call(**kwargs):
        return result

    monkeypatch.setattr(mcp_mod, "mint_mcp_access_token", lambda **k: "mcp-test-token")
    monkeypatch.setattr(mcp_mod, "_call_manage_incident_tickets_async", _fake_call)


def test_lookup_incident_detail_success(monkeypatch: pytest.MonkeyPatch):
    _patch_mcp_call(
        monkeypatch,
        {"ok": True, "action": "get", "data": _sample_incident(42)},
    )

    envelope = mcp_mod.lookup_incidents_via_mcp(
        incident_id=42,
        filters={},
        auth_header="Bearer test-token",
    )

    assert envelope["ok"] is True
    assert envelope["rows"][0]["origin"] == "branch"
    assert envelope["rows"][0]["id"] == 42


def test_lookup_incident_list_with_filters(monkeypatch: pytest.MonkeyPatch):
    _patch_mcp_call(
        monkeypatch,
        {"ok": True, "action": "list", "data": [_sample_incident()]},
    )

    envelope = mcp_mod.lookup_incidents_via_mcp(
        incident_id=None,
        filters={"status": "open", "branch": "miami_doral"},
        auth_header=None,
    )

    assert envelope["ok"] is True
    assert len(envelope["rows"]) == 1


def test_lookup_incident_empty_list(monkeypatch: pytest.MonkeyPatch):
    _patch_mcp_call(monkeypatch, {"ok": True, "action": "list", "data": []})

    envelope = mcp_mod.lookup_incidents_via_mcp(
        incident_id=None,
        filters={"status": "open"},
        auth_header=None,
    )

    assert envelope["ok"] is True
    assert envelope["reason"] == "empty"
    assert envelope["rows"] == []


def test_lookup_incident_not_found(monkeypatch: pytest.MonkeyPatch):
    _patch_mcp_call(
        monkeypatch,
        {
            "ok": False,
            "error_code": "UPSTREAM_NOT_FOUND",
            "message": "Incident not found.",
            "http_status": 404,
        },
    )

    envelope = mcp_mod.lookup_incidents_via_mcp(
        incident_id=999,
        filters={},
        auth_header="Bearer t",
    )

    assert envelope["ok"] is False
    assert envelope["reason"] == "not_found"


def test_lookup_incident_mcp_transport_failure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mcp_mod, "mint_mcp_access_token", lambda **k: "mcp-test-token")

    async def _fail(**kwargs):
        raise TimeoutError("mcp timeout")

    monkeypatch.setattr(mcp_mod, "_call_manage_incident_tickets_async", _fail)

    envelope = mcp_mod.lookup_incidents_via_mcp(
        incident_id=None,
        filters={},
        auth_header=None,
    )

    assert envelope["ok"] is False
    assert envelope["reason"] == "http_error"


def test_lookup_incident_token_mint_failure(monkeypatch: pytest.MonkeyPatch):
    def _fail(**kwargs):
        raise RuntimeError("mint failed")

    monkeypatch.setattr(mcp_mod, "mint_mcp_access_token", _fail)

    envelope = mcp_mod.lookup_incidents_via_mcp(
        incident_id=None,
        filters={},
        auth_header=None,
    )

    assert envelope["ok"] is False
    assert envelope["reason"] == "http_error"


def test_parse_tool_result_langchain_content_blocks():
    payload = {
        "ok": True,
        "action": "list",
        "data": [{"id": 55, "title": "Slow order", "status": "open", "origin": "customer", "branch": "miami_doral", "category": "customer_complaint", "description": "x"}],
    }
    raw = [{"type": "text", "text": json.dumps(payload)}]
    parsed = mcp_mod._parse_tool_result(raw)
    assert parsed["ok"] is True
    assert len(parsed["data"]) == 1


def test_parse_tool_result_json_string():
    raw = '{"ok": true, "action": "list", "data": []}'
    parsed = mcp_mod._parse_tool_result(raw)
    assert parsed["ok"] is True
    assert parsed["data"] == []


def test_lookup_incident_summary(monkeypatch: pytest.MonkeyPatch):
    summary = {
        "by_status": {"open": 3, "resolved": 10},
        "by_category": {"customer_complaint": 2},
        "by_origin": {"customer": 3},
        "by_branch": {"miami_doral": 3},
    }
    _patch_mcp_call(
        monkeypatch,
        {"ok": True, "action": "summary", "data": summary},
    )

    envelope = mcp_mod.lookup_incidents_via_mcp(
        incident_id=None,
        filters={},
        auth_header="Bearer test-token",
        incident_action="summary",
    )

    assert envelope["ok"] is True
    assert envelope["summary"] == summary
    assert envelope["action"] == "summary"


def test_mutate_incident_create_success(monkeypatch: pytest.MonkeyPatch):
    created = _sample_incident(101)
    _patch_mcp_call(
        monkeypatch,
        {"ok": True, "action": "create", "data": created},
    )

    envelope = mcp_mod.mutate_incident_via_mcp(
        write_action="create",
        auth_header="Bearer test-token",
        write_payload={
            "title": "Oven fault",
            "description": "Main oven not heating",
            "category": "equipment_failure",
            "origin": "branch",
            "branch": "miami_doral",
        },
    )

    assert envelope["ok"] is True
    assert envelope["action"] == "create"
    assert envelope["rows"][0]["id"] == 101


def test_mutate_incident_update_success(monkeypatch: pytest.MonkeyPatch):
    open_row = _sample_incident(42)
    in_progress = {**open_row, "status": "in_progress"}
    resolved = {**open_row, "status": "resolved"}
    calls: list[dict] = []

    async def _sequenced_call(**kwargs):
        arguments = kwargs.get("arguments") or {}
        calls.append(arguments)
        action = arguments.get("action")
        if action == "get":
            return {"ok": True, "action": "get", "data": open_row}
        if action == "update_status" and arguments.get("status") == "in_progress":
            return {"ok": True, "action": "update_status", "data": in_progress}
        if action == "update_status" and arguments.get("status") == "resolved":
            return {"ok": True, "action": "update_status", "data": resolved}
        return {"ok": False, "error_code": "UPSTREAM_ERROR", "message": "unexpected call"}

    monkeypatch.setattr(mcp_mod, "mint_mcp_access_token", lambda **k: "mcp-test-token")
    monkeypatch.setattr(mcp_mod, "_call_manage_incident_tickets_async", _sequenced_call)

    envelope = mcp_mod.mutate_incident_via_mcp(
        write_action="update_status",
        auth_header="Bearer test-token",
        incident_id=42,
        write_status="resolved",
    )

    assert envelope["ok"] is True
    assert envelope["action"] == "update_status"
    assert envelope["rows"][0]["status"] == "resolved"
    assert [call.get("action") for call in calls] == [
        "get",
        "update_status",
        "update_status",
    ]


def test_resolve_procedure_hint_for_incident_create():
    from agent.fallbacks import resolve_procedure_hint

    hint = resolve_procedure_hint("How do I create an incident")
    assert hint is not None
    assert "Create incident for" in hint

    assert resolve_procedure_hint("how do you create an incident?") is not None
