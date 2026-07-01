"""Centralized incident manager API tests."""

from __future__ import annotations

import uuid

import config
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    not config.DATABASE_URL,
    reason="DATABASE_URL not set — incident manager tests require PostgreSQL",
)


def _unique_title(prefix: str = "Incident"):  # noqa: ANN201
    return f"{prefix} {uuid.uuid4().hex[:10]}"


def test_create_incident_and_get_detail(auth_client: TestClient):
    create_resp = auth_client.post(
        "/api/incidents",
        json={
            "title": _unique_title("Equipment"),
            "description": "The fryer failed during lunch service.",
            "category": "equipment_failure",
            "status": "open",
            "origin": "branch",
            "branch": "medellin_centro",
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["id"] > 0
    assert created["status"] == "open"

    detail_resp = auth_client.get(f"/api/incidents/{created['id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["title"] == created["title"]


def test_create_incident_invalid_field_returns_400(auth_client: TestClient):
    resp = auth_client.post(
        "/api/incidents",
        json={
            "title": "",
            "description": "Missing title should fail.",
            "category": "equipment_failure",
            "status": "open",
            "origin": "branch",
            "branch": "medellin_centro",
        },
    )
    assert resp.status_code == 400
    body = resp.json()
    assert isinstance(body.get("detail"), dict)
    assert body["detail"]["field"] in {"title", "body"}


def test_list_incidents_filters_by_origin(auth_client: TestClient):
    auth_client.post(
        "/api/incidents",
        json={
            "title": _unique_title("Internal"),
            "description": "Internal QA detected a POS timeout issue.",
            "category": "pos_system",
            "status": "open",
            "origin": "internal",
            "branch": "central",
        },
    )

    resp = auth_client.get("/api/incidents", params={"origin": "internal"})
    assert resp.status_code == 200
    rows = resp.json()
    assert isinstance(rows, list)
    assert all(row["origin"] == "internal" for row in rows)


def test_status_transitions_and_final_state(auth_client: TestClient):
    created = auth_client.post(
        "/api/incidents",
        json={
            "title": _unique_title("Complaint"),
            "description": "Customer complained about long wait times.",
            "category": "customer_complaint",
            "status": "open",
            "origin": "customer",
            "branch": "central",
        },
    ).json()

    direct_resolve = auth_client.patch(
        f"/api/incidents/{created['id']}/status",
        json={"status": "resolved"},
    )
    assert direct_resolve.status_code == 400
    assert direct_resolve.json()["detail"]["field"] == "status"

    in_progress = auth_client.patch(
        f"/api/incidents/{created['id']}/status",
        json={"status": "in_progress"},
    )
    assert in_progress.status_code == 200
    assert in_progress.json()["status"] == "in_progress"

    resolved = auth_client.patch(
        f"/api/incidents/{created['id']}/status",
        json={"status": "resolved"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    cannot_reopen = auth_client.patch(
        f"/api/incidents/{created['id']}/status",
        json={"status": "in_progress"},
    )
    assert cannot_reopen.status_code == 400


def test_summary_endpoint_returns_grouped_totals(auth_client: TestClient):
    resp = auth_client.get("/api/incidents/summary")
    assert resp.status_code == 200
    payload = resp.json()
    assert "by_status" in payload
    assert "by_category" in payload
    assert "by_origin" in payload
    assert "by_branch" in payload
    assert set(payload["by_status"]).issuperset(
        {"open", "in_progress", "resolved", "discarded"}
    )

