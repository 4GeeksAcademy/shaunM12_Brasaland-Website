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


def test_update_other_user_forbidden(anon_client: TestClient):
    anon_client.post(
        "/auth/register",
        json={"email": "alice@brasaland.com", "password": "supersecret"},
    )
    anon_client.post(
        "/auth/register",
        json={"email": "bob@brasaland.com", "password": "supersecret"},
    )
    token_a = anon_client.post(
        "/auth/login",
        data={"username": "alice@brasaland.com", "password": "supersecret"},
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    users = anon_client.get("/users", headers=headers_a).json()
    bob_id = next(u["id"] for u in users if u["email"] == "bob@brasaland.com")

    response = anon_client.put(
        f"/users/{bob_id}",
        headers=headers_a,
        json={"email": "hijack@brasaland.com"},
    )
    assert response.status_code == 403
