"""Password-reset flow API tests (AUTH-03)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _register(client: TestClient, email: str, password: str = "supersecret") -> None:
    client.post("/auth/register", json={"email": email, "password": password})


def _capture_token(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Patch the route's email sender to capture the issued reset token."""
    import auth.routes as routes

    captured: dict = {}

    def fake_send(to: str, token: str) -> None:
        captured["to"] = to
        captured["token"] = token

    monkeypatch.setattr(routes, "send_password_reset_email", fake_send)
    return captured


def test_forgot_password_always_200(anon_client: TestClient):
    _register(anon_client, "exists@brasaland.com")

    found = anon_client.post(
        "/auth/forgot-password", json={"email": "exists@brasaland.com"}
    )
    unknown = anon_client.post(
        "/auth/forgot-password", json={"email": "nobody@brasaland.com"}
    )

    assert found.status_code == 200
    assert unknown.status_code == 200
    # Identical body — no enumeration signal.
    assert found.json() == unknown.json()


def test_forgot_password_emails_existing_user(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured = _capture_token(monkeypatch)
    _register(anon_client, "reset@brasaland.com")

    anon_client.post("/auth/forgot-password", json={"email": "reset@brasaland.com"})
    assert captured.get("to") == "reset@brasaland.com"
    assert captured.get("token")


def test_forgot_password_unknown_email_sends_nothing(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured = _capture_token(monkeypatch)
    anon_client.post("/auth/forgot-password", json={"email": "ghost@brasaland.com"})
    assert captured == {}


def test_reset_password_happy_path(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured = _capture_token(monkeypatch)
    _register(anon_client, "happy@brasaland.com", "oldpassword")
    anon_client.post("/auth/forgot-password", json={"email": "happy@brasaland.com"})

    resp = anon_client.post(
        "/auth/reset-password",
        json={"token": captured["token"], "new_password": "brandnewpass"},
    )
    assert resp.status_code == 200

    # New password works; old one no longer does.
    new_login = anon_client.post(
        "/auth/login",
        data={"username": "happy@brasaland.com", "password": "brandnewpass"},
    )
    old_login = anon_client.post(
        "/auth/login",
        data={"username": "happy@brasaland.com", "password": "oldpassword"},
    )
    assert new_login.status_code == 200
    assert old_login.status_code == 401


def test_reset_password_invalid_token(anon_client: TestClient):
    resp = anon_client.post(
        "/auth/reset-password",
        json={"token": "not-a-real-jwt", "new_password": "brandnewpass"},
    )
    assert resp.status_code == 400


def test_reset_password_wrong_token_type_rejected(anon_client: TestClient):
    """A validly-signed JWT that isn't a reset token (no ``type``) is refused."""
    from auth.security import create_access_token

    # An access token is signed with the same secret but lacks the reset ``type``.
    bad = create_access_token(1)
    resp = anon_client.post(
        "/auth/reset-password",
        json={"token": bad, "new_password": "brandnewpass"},
    )
    assert resp.status_code == 400


def test_reset_password_unknown_user_rejected(anon_client: TestClient):
    """A well-formed reset token whose subject is not a real user is refused."""
    from auth.security import create_password_reset_token

    token = create_password_reset_token(user_id=999999, jti="orphan-jti")
    resp = anon_client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "brandnewpass"},
    )
    assert resp.status_code == 400


def test_reset_password_expired_token(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    import config

    captured = _capture_token(monkeypatch)
    _register(anon_client, "expired@brasaland.com")
    # Issue a token that is already expired.
    monkeypatch.setattr(config, "PASSWORD_RESET_EXPIRES_MINUTES", -1)
    anon_client.post("/auth/forgot-password", json={"email": "expired@brasaland.com"})

    resp = anon_client.post(
        "/auth/reset-password",
        json={"token": captured["token"], "new_password": "brandnewpass"},
    )
    assert resp.status_code == 400


def test_reset_password_single_use(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured = _capture_token(monkeypatch)
    _register(anon_client, "once@brasaland.com")
    anon_client.post("/auth/forgot-password", json={"email": "once@brasaland.com"})

    first = anon_client.post(
        "/auth/reset-password",
        json={"token": captured["token"], "new_password": "brandnewpass"},
    )
    second = anon_client.post(
        "/auth/reset-password",
        json={"token": captured["token"], "new_password": "anotherpass1"},
    )
    assert first.status_code == 200
    assert second.status_code == 400


def test_requesting_new_link_supersedes_old(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured = _capture_token(monkeypatch)
    _register(anon_client, "super@brasaland.com")

    anon_client.post("/auth/forgot-password", json={"email": "super@brasaland.com"})
    first_token = captured["token"]
    anon_client.post("/auth/forgot-password", json={"email": "super@brasaland.com"})
    second_token = captured["token"]

    # The first (older) link is now invalid; the latest one works.
    old = anon_client.post(
        "/auth/reset-password",
        json={"token": first_token, "new_password": "brandnewpass"},
    )
    new = anon_client.post(
        "/auth/reset-password",
        json={"token": second_token, "new_password": "brandnewpass"},
    )
    assert old.status_code == 400
    assert new.status_code == 200


def test_reset_password_weak_password_rejected(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured = _capture_token(monkeypatch)
    _register(anon_client, "weak@brasaland.com")
    anon_client.post("/auth/forgot-password", json={"email": "weak@brasaland.com"})

    resp = anon_client.post(
        "/auth/reset-password",
        json={"token": captured["token"], "new_password": "short"},
    )
    assert resp.status_code == 422


def test_reset_revokes_refresh_tokens(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured = _capture_token(monkeypatch)
    _register(anon_client, "session@brasaland.com")
    anon_client.post(
        "/auth/login",
        data={"username": "session@brasaland.com", "password": "supersecret"},
    )
    # The refresh cookie is valid right now.
    assert anon_client.post("/auth/refresh").status_code == 200

    anon_client.post("/auth/forgot-password", json={"email": "session@brasaland.com"})
    anon_client.post(
        "/auth/reset-password",
        json={"token": captured["token"], "new_password": "brandnewpass"},
    )
    # After the reset, the previously-issued refresh token is revoked.
    assert anon_client.post("/auth/refresh").status_code == 401


def test_rate_limit_returns_429(anon_client: TestClient):
    email = "spam@brasaland.com"
    for _ in range(10):
        assert (
            anon_client.post("/auth/forgot-password", json={"email": email}).status_code
            == 200
        )
    # The 11th request within the hour is rate-limited.
    assert (
        anon_client.post("/auth/forgot-password", json={"email": email}).status_code
        == 429
    )


def test_forgot_password_records_forwarded_client_ip(anon_client: TestClient):
    """The audit row should capture the first hop of ``X-Forwarded-For``."""
    import database

    _register(anon_client, "ipuser@brasaland.com")
    anon_client.post(
        "/auth/forgot-password",
        json={"email": "ipuser@brasaland.com"},
        headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1"},
    )
    ips = [row.get("ip") for row in database.get_auth_audit_table().all()]
    assert "203.0.113.7" in ips


def test_audit_log_records_events(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    import database

    captured = _capture_token(monkeypatch)
    _register(anon_client, "audit@brasaland.com")
    anon_client.post("/auth/forgot-password", json={"email": "audit@brasaland.com"})
    anon_client.post(
        "/auth/reset-password",
        json={"token": captured["token"], "new_password": "brandnewpass"},
    )

    events = [row["event"] for row in database.get_auth_audit_table().all()]
    assert "password_reset_requested" in events
    assert "password_reset_completed" in events
