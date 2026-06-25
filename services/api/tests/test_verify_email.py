"""Endpoint decision tests for ``POST /auth/verify-email`` and
``/auth/resend-verification``.

Assertions target the verification decision (did the account become verified?
was an invalid token refused?), not the response body.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _register_and_token(client: TestClient, email: str, password: str = "supersecret"):
    client.post("/auth/register", json={"email": email, "password": password})
    token = client.post(
        "/auth/login", data={"username": email, "password": password}
    ).json()["access_token"]
    user_id = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    ).json()["id"]
    return user_id, token


# --- Happy path --------------------------------------------------------------


def test_valid_token_marks_user_verified(anon_client: TestClient):
    user_id, token = _register_and_token(anon_client, "verify@brasaland.com")
    from auth import verifications

    raw = verifications.issue_verification_token(user_id)
    resp = anon_client.post("/auth/verify-email", json={"token": raw})
    assert resp.status_code == 200

    # The decision is observable on the user record.
    me = anon_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["is_verified"] is True


# --- Edge cases --------------------------------------------------------------


def test_token_cannot_be_used_twice(anon_client: TestClient):
    user_id, _ = _register_and_token(anon_client, "once@brasaland.com")
    from auth import verifications

    raw = verifications.issue_verification_token(user_id)
    assert anon_client.post("/auth/verify-email", json={"token": raw}).status_code == 200
    # Replaying the same token is refused.
    assert anon_client.post("/auth/verify-email", json={"token": raw}).status_code == 400


def test_resend_short_circuits_when_already_verified(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    user_id, token = _register_and_token(anon_client, "already@brasaland.com")
    from auth import verifications
    import auth.routes as routes

    # Verify first.
    raw = verifications.issue_verification_token(user_id)
    anon_client.post("/auth/verify-email", json={"token": raw})

    sent = {"count": 0}

    def fake_send(*_a, **_k):
        sent["count"] += 1

    monkeypatch.setattr(routes, "send_verification_email", fake_send)

    resp = anon_client.post(
        "/auth/resend-verification", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    # The decision: no new email is issued for an already-verified user.
    assert sent["count"] == 0


# --- Failure modes -----------------------------------------------------------


def test_bogus_token_is_rejected(anon_client: TestClient):
    resp = anon_client.post("/auth/verify-email", json={"token": "not-a-real-token"})
    assert resp.status_code == 400


def test_expired_token_is_rejected(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    user_id, _ = _register_and_token(anon_client, "stale@brasaland.com")
    import config
    from auth import verifications

    monkeypatch.setattr(config, "EMAIL_VERIFICATION_EXPIRES_HOURS", -1)
    raw = verifications.issue_verification_token(user_id)
    resp = anon_client.post("/auth/verify-email", json={"token": raw})
    assert resp.status_code == 400
