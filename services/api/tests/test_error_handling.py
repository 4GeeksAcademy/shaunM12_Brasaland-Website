"""Error-handling regression tests (context-9 ERR-01).

Verify that internal failures surface as clean, generic, client-safe responses —
never raw library errors, stack traces, or secrets.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_incident_upload_malformed_csv_returns_generic_message(client: TestClient):
    # Invalid (non-UTF8) bytes make pandas raise; the raw parser error must be
    # logged server-side and replaced with a curated message in the response.
    resp = client.post(
        "/incidents/analyze",
        files={"file": ("bad.csv", b"\xff\xfe\x00\x01\x02\x03garbage", "text/csv")},
    )

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail == "Incorrect format: the file could not be read as a valid CSV."
    # No pandas/parser internals leaked to the client.
    for leaked in ("tokeniz", "Traceback", "pandas", "0x"):
        assert leaked.lower() not in detail.lower()


def test_incident_upload_empty_csv_returns_generic_message(client: TestClient):
    resp = client.post(
        "/incidents/analyze",
        files={"file": ("empty.csv", b"   ", "text/csv")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Empty file: the CSV has no content."


def test_incident_upload_and_export_routes_succeed(client: TestClient):
    csv_payload = (
        b"incident_id,date,location_id,category,description,status,reporter_id\n"
        b"BRS-000001,2026-07-28,COL-01,EQUIPMENT,Grill requires service,OPEN,MGR-01\n"
    )

    analyze = client.post(
        "/incidents/analyze",
        files={"file": ("incidents.csv", csv_payload, "text/csv")},
    )

    assert analyze.status_code == 200
    assert analyze.json()["totalProcessed"] == 1
    assert analyze.json()["validCount"] == 1

    export = client.get("/incidents/results/export")

    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    assert "results.csv" in export.headers["content-disposition"]


def test_resend_verification_provider_failure_is_clean(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    import auth.routes as routes

    def boom(*_args, **_kwargs):
        # Simulate a provider error whose raw text contains a secret.
        raise RuntimeError("Resend 401: api_key=sk_live_SUPERSECRET leaked")

    monkeypatch.setattr(routes, "send_verification_email", boom)

    resp = auth_client.post("/auth/resend-verification")

    assert resp.status_code == 502
    body = resp.text
    assert "SUPERSECRET" not in body
    assert "api_key" not in body
    assert resp.json()["detail"] == (
        "We couldn't send the verification email right now. Please try again later."
    )
