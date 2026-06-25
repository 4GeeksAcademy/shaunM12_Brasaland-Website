"""Endpoint decision tests for ``GET /auth/me`` and the user-management authz.

These exercise the access-control decisions the auth layer enforces on the
``/users`` routes (who may read the list, who may modify whom).
"""

from __future__ import annotations

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


# --- GET /auth/me ------------------------------------------------------------


def test_me_returns_current_user_without_password_hash(anon_client: TestClient):
    _, token = _register_and_token(anon_client, "me@brasaland.com")
    resp = anon_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@brasaland.com"
    # The decision: the password hash is never exposed.
    assert "hashed_password" not in body


def test_me_requires_a_token(anon_client: TestClient):
    assert anon_client.get("/auth/me").status_code == 401


def test_me_rejects_a_malformed_token(anon_client: TestClient):
    resp = anon_client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert resp.status_code == 401


# --- User-management authz ---------------------------------------------------


def test_user_may_update_their_own_record(anon_client: TestClient):
    user_id, token = _register_and_token(anon_client, "self@brasaland.com")
    resp = anon_client.put(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Renamed"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"


def test_user_cannot_update_another_user(anon_client: TestClient):
    _, token_a = _register_and_token(anon_client, "alice@brasaland.com")
    bob_id, _ = _register_and_token(anon_client, "bob@brasaland.com")

    resp = anon_client.put(
        f"/users/{bob_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"email": "hijack@brasaland.com"},
    )
    assert resp.status_code == 403


def test_non_admin_cannot_list_users(anon_client: TestClient):
    _, token = _register_and_token(anon_client, "plain@brasaland.com")
    resp = anon_client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_protected_supplier_route_requires_auth(anon_client: TestClient):
    """A representative protected resource is gated by the auth dependency."""
    assert anon_client.get("/api/suppliers").status_code == 401
