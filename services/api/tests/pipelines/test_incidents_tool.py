"""Unit tests for incident lookup tool (mocked HTTP — P2-L12)."""

from __future__ import annotations

import pytest

from agent.tools import incidents as incidents_mod


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


def test_lookup_incident_detail_success(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    def _fetch(method, path, *, params=None, headers=None, timeout=None):
        captured["method"] = method
        captured["path"] = path
        captured["headers"] = headers
        return 200, _sample_incident(42), None

    monkeypatch.setattr(incidents_mod, "fetch_json", _fetch)

    envelope = incidents_mod.lookup_incidents(
        incident_id=42,
        filters={},
        auth_header="Bearer test-token",
    )

    assert envelope["ok"] is True
    assert envelope["rows"][0]["origin"] == "branch"
    assert envelope["rows"][0]["id"] == 42
    assert captured["path"] == "/incidents/42"
    assert captured["headers"]["Authorization"] == "Bearer test-token"


def test_lookup_incident_list_with_filters(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    def _fetch(method, path, *, params=None, headers=None, timeout=None):
        captured["params"] = params
        return 200, [_sample_incident()], None

    monkeypatch.setattr(incidents_mod, "fetch_json", _fetch)

    envelope = incidents_mod.lookup_incidents(
        incident_id=None,
        filters={"status": "open", "branch": "miami_doral"},
        auth_header=None,
    )

    assert envelope["ok"] is True
    assert len(envelope["rows"]) == 1
    assert captured["params"] == {"status": "open", "branch": "miami_doral"}


def test_lookup_incident_empty_list(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        incidents_mod,
        "fetch_json",
        lambda *a, **k: (200, [], None),
    )

    envelope = incidents_mod.lookup_incidents(
        incident_id=None,
        filters={"status": "open"},
        auth_header=None,
    )

    assert envelope["ok"] is True
    assert envelope["reason"] == "empty"
    assert envelope["rows"] == []


def test_lookup_incident_not_found(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        incidents_mod,
        "fetch_json",
        lambda *a, **k: (404, {"detail": "Not found"}, None),
    )

    envelope = incidents_mod.lookup_incidents(
        incident_id=999,
        filters={},
        auth_header="Bearer t",
    )

    assert envelope["ok"] is False
    assert envelope["reason"] == "not_found"


def test_lookup_incident_timeout(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        incidents_mod,
        "fetch_json",
        lambda *a, **k: (0, None, "timeout"),
    )

    envelope = incidents_mod.lookup_incidents(
        incident_id=None,
        filters={},
        auth_header=None,
    )

    assert envelope["ok"] is False
    assert envelope["reason"] == "timeout"


def test_lookup_incident_http_401(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        incidents_mod,
        "fetch_json",
        lambda *a, **k: (401, {"detail": "Unauthorized"}, None),
    )

    envelope = incidents_mod.lookup_incidents(
        incident_id=None,
        filters={},
        auth_header=None,
    )

    assert envelope["ok"] is False
    assert envelope["reason"] == "http_401"
