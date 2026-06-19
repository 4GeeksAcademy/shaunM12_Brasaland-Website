"""Authentication and user-management API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from auth.security import hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("supersecret")
    assert hashed != "supersecret"
    assert verify_password("supersecret", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_register_returns_token(anon_client: TestClient):
    response = anon_client.post(
        "/auth/register",
        json={"email": "new@brasaland.com", "password": "supersecret"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_login_success_and_failure(anon_client: TestClient):
    anon_client.post(
        "/auth/register",
        json={"email": "login@brasaland.com", "password": "supersecret"},
    )

    ok = anon_client.post(
        "/auth/login",
        data={"username": "login@brasaland.com", "password": "supersecret"},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = anon_client.post(
        "/auth/login",
        data={"username": "login@brasaland.com", "password": "wrong"},
    )
    assert bad.status_code == 401


def test_duplicate_email_rejected(anon_client: TestClient):
    payload = {"email": "dupe@brasaland.com", "password": "supersecret"}
    first = anon_client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = anon_client.post("/auth/register", json=payload)
    assert second.status_code == 400


def test_me_requires_token(anon_client: TestClient):
    assert anon_client.get("/auth/me").status_code == 401


def test_me_with_token(auth_client: TestClient):
    response = auth_client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "user@brasaland.com"
    assert "hashed_password" not in response.json()


def test_protected_supplier_route_requires_auth(anon_client: TestClient):
    assert anon_client.get("/api/suppliers").status_code == 401


def _register_and_token(client: TestClient, email: str, password: str = "supersecret"):
    """Register a user, returning ``(user_id, bearer_token)``."""
    client.post("/auth/register", json={"email": email, "password": password})
    token = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    ).json()["access_token"]
    user_id = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()[
        "id"
    ]
    return user_id, token


def test_update_other_user_forbidden(anon_client: TestClient):
    _, token_a = _register_and_token(anon_client, "alice@brasaland.com")
    bob_id, _ = _register_and_token(anon_client, "bob@brasaland.com")

    response = anon_client.put(
        f"/users/{bob_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"email": "hijack@brasaland.com"},
    )
    assert response.status_code == 403


def test_register_accepts_name(anon_client: TestClient):
    anon_client.post(
        "/auth/register",
        json={
            "email": "named@brasaland.com",
            "password": "supersecret",
            "name": "Named User",
        },
    )
    token = anon_client.post(
        "/auth/login",
        data={"username": "named@brasaland.com", "password": "supersecret"},
    ).json()["access_token"]
    me = anon_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert me["name"] == "Named User"
    assert me["is_verified"] is False


def test_login_sets_refresh_cookie(anon_client: TestClient):
    anon_client.post(
        "/auth/register",
        json={"email": "cookie@brasaland.com", "password": "supersecret"},
    )
    resp = anon_client.post(
        "/auth/login",
        data={"username": "cookie@brasaland.com", "password": "supersecret"},
    )
    assert resp.status_code == 200
    assert "brasaland_refresh" in resp.cookies


def test_refresh_rotates_and_returns_access_token(anon_client: TestClient):
    anon_client.post(
        "/auth/register",
        json={"email": "refresh@brasaland.com", "password": "supersecret"},
    )
    anon_client.post(
        "/auth/login",
        data={"username": "refresh@brasaland.com", "password": "supersecret"},
    )
    # TestClient persists the refresh cookie set on login.
    refreshed = anon_client.post("/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


def test_refresh_without_cookie_unauthorized(anon_client: TestClient):
    assert anon_client.post("/auth/refresh").status_code == 401


def test_logout_revokes_refresh_token(anon_client: TestClient):
    anon_client.post(
        "/auth/register",
        json={"email": "logout@brasaland.com", "password": "supersecret"},
    )
    login = anon_client.post(
        "/auth/login",
        data={"username": "logout@brasaland.com", "password": "supersecret"},
    )
    raw_refresh = login.cookies.get("brasaland_refresh")

    assert anon_client.post("/auth/logout").status_code == 200

    # The revoked token can no longer be used to refresh.
    anon_client.cookies.set("brasaland_refresh", raw_refresh)
    assert anon_client.post("/auth/refresh").status_code == 401


def test_verify_email_flow(anon_client: TestClient):
    user_id, _ = _register_and_token(anon_client, "verify@brasaland.com")

    from auth import verifications as verifications_mod

    raw = verifications_mod.issue_verification_token(user_id)
    resp = anon_client.post("/auth/verify-email", json={"token": raw})
    assert resp.status_code == 200

    token = anon_client.post(
        "/auth/login",
        data={"username": "verify@brasaland.com", "password": "supersecret"},
    ).json()["access_token"]
    me = anon_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert me["is_verified"] is True


def test_verify_email_rejects_bad_token(anon_client: TestClient):
    resp = anon_client.post("/auth/verify-email", json={"token": "not-a-real-token"})
    assert resp.status_code == 400


def test_list_users_requires_admin(anon_client: TestClient):
    _, token = _register_and_token(anon_client, "plain@brasaland.com")
    resp = anon_client.get(
        "/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
