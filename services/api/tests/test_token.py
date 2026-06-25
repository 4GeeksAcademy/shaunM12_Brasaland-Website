"""Endpoint decision tests for the session-token lifecycle.

Covers ``POST /auth/refresh``, ``/auth/logout`` and ``/auth/logout-all``.
Assertions target what the endpoint decides about a session (rotate it, end it,
end all of them), proven by whether the session still works afterwards.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from users.models import UserUpdate
from users.repository import get_user_record_by_email, update_user


def _register_and_login(client: TestClient, email: str, password: str = "supersecret"):
    client.post("/auth/register", json={"email": email, "password": password})
    return client.post(
        "/auth/login", data={"username": email, "password": password}
    )


# --- /auth/refresh -----------------------------------------------------------


def test_refresh_rotates_into_a_new_access_token(anon_client: TestClient):
    _register_and_login(anon_client, "rot@brasaland.com")
    resp = anon_client.post("/auth/refresh")  # TestClient resends the cookie
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_refresh_without_cookie_is_rejected(anon_client: TestClient):
    assert anon_client.post("/auth/refresh").status_code == 401


def test_refresh_is_refused_for_a_user_deactivated_after_login(anon_client: TestClient):
    """A user disabled after issuing a refresh token must not regain a session."""
    _register_and_login(anon_client, "disabled@brasaland.com")
    user = get_user_record_by_email("disabled@brasaland.com")
    update_user(user.id, UserUpdate(is_active=False))

    resp = anon_client.post("/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Inactive user"


def test_reused_refresh_token_is_rejected(anon_client: TestClient):
    """After rotation the previous refresh token must stop working (theft guard)."""
    login = _register_and_login(anon_client, "reuse@brasaland.com")
    old_cookie = login.cookies.get("brasaland_refresh")

    # Rotate once (consumes the old token, sets a new cookie).
    assert anon_client.post("/auth/refresh").status_code == 200

    # Replay the original token explicitly.
    anon_client.cookies.set("brasaland_refresh", old_cookie)
    assert anon_client.post("/auth/refresh").status_code == 401


# --- /auth/logout ------------------------------------------------------------


def test_logout_revokes_the_refresh_session(anon_client: TestClient):
    login = _register_and_login(anon_client, "logout@brasaland.com")
    raw = login.cookies.get("brasaland_refresh")

    assert anon_client.post("/auth/logout").status_code == 200

    # The decision: the revoked token can no longer refresh.
    anon_client.cookies.set("brasaland_refresh", raw)
    assert anon_client.post("/auth/refresh").status_code == 401


def test_logout_without_cookie_is_a_noop_success(anon_client: TestClient):
    assert anon_client.post("/auth/logout").status_code == 200


# --- /auth/logout-all --------------------------------------------------------


def test_logout_all_ends_every_session(anon_client: TestClient):
    login = _register_and_login(anon_client, "all@brasaland.com")
    token = anon_client.post(
        "/auth/login", data={"username": "all@brasaland.com", "password": "supersecret"}
    ).json()["access_token"]
    raw = login.cookies.get("brasaland_refresh")

    resp = anon_client.post(
        "/auth/logout-all", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200

    # Even an older session's refresh token is now dead.
    anon_client.cookies.set("brasaland_refresh", raw)
    assert anon_client.post("/auth/refresh").status_code == 401


def test_logout_all_requires_authentication(anon_client: TestClient):
    assert anon_client.post("/auth/logout-all").status_code == 401
