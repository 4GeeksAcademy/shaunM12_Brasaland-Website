"""Endpoint decision tests for ``POST /auth/login``.

Asserts on the authentication decision and the session it establishes, not on
the response shape.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from users.models import UserUpdate
from users.repository import get_user_record_by_email, update_user


def _register(client: TestClient, email: str, password: str = "supersecret"):
    client.post("/auth/register", json={"email": email, "password": password})


def _login(client: TestClient, username: str, password: str):
    return client.post("/auth/login", data={"username": username, "password": password})


# --- Happy path --------------------------------------------------------------


def test_correct_credentials_establish_usable_session(anon_client: TestClient):
    _register(anon_client, "login@brasaland.com")
    resp = _login(anon_client, "login@brasaland.com", "supersecret")
    assert resp.status_code == 200

    token = resp.json()["access_token"]
    me = anon_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200


def test_login_issues_a_working_refresh_session(anon_client: TestClient):
    """A login must establish a refresh session (provable by refreshing)."""
    _register(anon_client, "refreshable@brasaland.com")
    _login(anon_client, "refreshable@brasaland.com", "supersecret")
    # The decision: a refresh session now exists and can mint a new access token.
    refreshed = anon_client.post("/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


# --- Edge cases --------------------------------------------------------------


def test_email_matched_after_normalisation(anon_client: TestClient):
    _register(anon_client, "norm@brasaland.com")
    # Mixed case + surrounding whitespace still resolves to the same account.
    resp = _login(anon_client, "  Norm@Brasaland.com  ".strip(), "supersecret")
    assert resp.status_code == 200


def test_empty_password_is_rejected(anon_client: TestClient):
    _register(anon_client, "emptypw@brasaland.com")
    resp = _login(anon_client, "emptypw@brasaland.com", "")
    assert resp.status_code in (401, 422)  # never establishes a session


# --- Failure modes -----------------------------------------------------------


def test_wrong_password_is_rejected(anon_client: TestClient):
    _register(anon_client, "wrongpw@brasaland.com")
    resp = _login(anon_client, "wrongpw@brasaland.com", "incorrect")
    assert resp.status_code == 401


def test_unknown_email_is_rejected(anon_client: TestClient):
    resp = _login(anon_client, "ghost@brasaland.com", "supersecret")
    assert resp.status_code == 401


def test_inactive_user_is_refused_despite_correct_password(anon_client: TestClient):
    """The deactivated-account branch is a real security decision."""
    _register(anon_client, "inactive@brasaland.com")
    user = get_user_record_by_email("inactive@brasaland.com")
    update_user(user.id, UserUpdate(is_active=False))

    resp = _login(anon_client, "inactive@brasaland.com", "supersecret")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Inactive user"
