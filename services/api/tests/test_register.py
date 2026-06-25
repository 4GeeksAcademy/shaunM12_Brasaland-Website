"""Endpoint decision tests for ``POST /auth/register``.

Drives the route via TestClient but asserts on the *decision* (was the account
created? does it yield a usable session? is a bad request refused?), not on the
response envelope.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _register(client: TestClient, **payload):
    return client.post("/auth/register", json=payload)


# --- Happy path --------------------------------------------------------------


def test_register_creates_usable_session(anon_client: TestClient):
    resp = _register(anon_client, email="new@brasaland.com", password="supersecret")
    assert resp.status_code == 201

    token = resp.json()["access_token"]
    # The decision we care about: the token authenticates the new user.
    me = anon_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new@brasaland.com"
    # A new account starts unverified.
    assert me.json()["is_verified"] is False


def test_register_stores_optional_name(anon_client: TestClient):
    token = _register(
        anon_client, email="named@brasaland.com", password="supersecret", name="Ana"
    ).json()["access_token"]
    me = anon_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["name"] == "Ana"


# --- Edge cases --------------------------------------------------------------


def test_duplicate_email_is_rejected(anon_client: TestClient):
    _register(anon_client, email="dupe@brasaland.com", password="supersecret")
    second = _register(anon_client, email="dupe@brasaland.com", password="supersecret")
    assert second.status_code == 400


def test_email_is_normalised_so_case_variants_collide(anon_client: TestClient):
    """Registering the same address in different case must be treated as a dupe."""
    first = _register(anon_client, email="Casey@Brasaland.com", password="supersecret")
    assert first.status_code == 201
    second = _register(anon_client, email="casey@brasaland.com", password="supersecret")
    assert second.status_code == 400


def test_password_at_72_byte_boundary_is_accepted(anon_client: TestClient):
    resp = _register(anon_client, email="boundary@brasaland.com", password="a" * 72)
    assert resp.status_code == 201


# --- Failure modes -----------------------------------------------------------


def test_short_password_is_rejected(anon_client: TestClient):
    resp = _register(anon_client, email="weak@brasaland.com", password="short")
    assert resp.status_code == 422  # validation decision, no account created


def test_password_over_72_bytes_is_rejected(anon_client: TestClient):
    resp = _register(anon_client, email="toolong@brasaland.com", password="a" * 73)
    assert resp.status_code == 422


def test_verification_email_failure_does_not_block_signup(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    """A provider outage must never cost a registration."""
    import auth.routes as routes

    def boom(*_a, **_k):
        raise RuntimeError("provider down")

    monkeypatch.setattr(routes, "send_verification_email", boom)

    resp = _register(anon_client, email="resilient@brasaland.com", password="supersecret")
    assert resp.status_code == 201
    # The account is genuinely usable despite the email failure.
    login = anon_client.post(
        "/auth/login",
        data={"username": "resilient@brasaland.com", "password": "supersecret"},
    )
    assert login.status_code == 200
