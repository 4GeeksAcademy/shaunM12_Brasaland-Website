"""Telemetry ingestion endpoint tests."""

from __future__ import annotations

import config
import pytest
from fastapi.testclient import TestClient


def test_telemetry_events_accepts_valid_batch(
    anon_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    # Phase 2 compatibility: stub endpoint returns only {"received": N}.
    monkeypatch.setattr(config, "TELEMETRY_PHASE_MODE", "stub")
    payload = {
        "events": [
            {
                "eventId": "f7a12edb-2a96-4964-8f8c-bc5d59fca4e8",
                "timestamp": "2026-07-08T18:00:00Z",
                "sessionId": "sess_abc123",
                "userId": "anonymous",
                "event_type": "ingredient_list_viewed",
                "schemaVersion": 1,
                "requestId": "req_abc123",
                "service": "backoffice",
                "properties": {"location_id": 1, "product_count": 42},
            }
        ]
    }
    response = anon_client.post("/telemetry/events", json=payload)
    assert response.status_code == 200
    assert response.json() == {"received": 1}


def test_telemetry_events_rejects_invalid_envelope_in_stub_mode(
    anon_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(config, "TELEMETRY_PHASE_MODE", "stub")
    payload = {
        "events": [
            {
                # missing eventId -> invalid envelope
                "timestamp": "2026-07-08T18:00:00Z",
                "sessionId": "sess_abc123",
                "userId": "anonymous",
                "event_type": "ingredient_list_viewed",
                "schemaVersion": 1,
                "requestId": "req_abc123",
                "service": "backoffice",
                "properties": {},
            },
            {
                "eventId": "f7a12edb-2a96-4964-8f8c-bc5d59fca4e8",
                "timestamp": "2026-07-08T18:00:00Z",
                "sessionId": "sess_abc123",
                "userId": "anonymous",
                "event_type": "ingredient_list_viewed",
                "schemaVersion": 1,
                "requestId": "req_abc123",
                "service": "backoffice",
                "properties": {"location_id": 1, "product_count": 42},
            },
        ]
    }
    response = anon_client.post("/telemetry/events", json=payload)
    assert response.status_code == 422


def test_telemetry_events_storage_mode_supports_mixed_batches(
    anon_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(config, "TELEMETRY_PHASE_MODE", "storage")
    payload = {
        "events": [
            {
                # missing eventId -> invalid envelope
                "timestamp": "2026-07-08T18:00:00Z",
                "sessionId": "sess_abc123",
                "userId": "anonymous",
                "event_type": "ingredient_list_viewed",
                "schemaVersion": 1,
                "requestId": "req_abc123",
                "service": "backoffice",
                "properties": {},
            },
            {
                "eventId": "f7a12edb-2a96-4964-8f8c-bc5d59fca4e8",
                "timestamp": "2026-07-08T18:00:00Z",
                "sessionId": "sess_abc123",
                "userId": "anonymous",
                "event_type": "ingredient_list_viewed",
                "schemaVersion": 1,
                "requestId": "req_abc123",
                "service": "backoffice",
                "properties": {"location_id": 1, "product_count": 42},
            },
        ]
    }
    response = anon_client.post("/telemetry/events", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["received"] == 2
    assert body["rejected"] == 1
    assert body["stored"] in {0, 1}

