"""Shared pytest fixtures for the Brasaland API test suite.

Each fixture rebuilds the app against a throwaway TinyDB file so tests are
isolated. New auth/users modules use lazy ``database.get_users_table()`` access,
so only ``database``, ``suppliers.repository`` and ``main`` need reloading.
"""

from __future__ import annotations

import os

# Ensure the auth layer has a signing secret during tests, even when no .env is
# present (e.g. CI). Real environment values still take precedence.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("ACCESS_TOKEN_EXPIRES_MINUTES", "30")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("REFRESH_TOKEN_EXPIRES_DAYS", "7")
os.environ.setdefault("REFRESH_COOKIE_NAME", "brasaland_refresh")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("EMAIL_VERIFICATION_EXPIRES_HOURS", "24")
os.environ.setdefault("FRONTEND_BASE_URL", "http://localhost:3000")
os.environ.setdefault("PASSWORD_RESET_EXPIRES_MINUTES", "30")
os.environ.setdefault("RESET_REQUESTS_PER_HOUR", "10")
os.environ.setdefault("EMAIL_PROVIDER", "console")

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _build_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("SUPPLIERS_DB_PATH", str(tmp_path / "suppliers.json"))
    monkeypatch.setenv("USERS_DB_PATH", str(tmp_path / "users.json"))
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "auth.json"))

    import database

    importlib.reload(database)
    database._db = None
    database._users_db = None
    database._auth_db = None

    import suppliers.repository

    importlib.reload(suppliers.repository)

    import main

    importlib.reload(main)
    return main


@pytest.fixture()
def anon_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Unauthenticated client against the real app (auth enforced)."""
    main = _build_app(monkeypatch, tmp_path)
    with TestClient(main.app) as test_client:
        yield test_client

    import database

    database._db = None
    database._users_db = None
    database._auth_db = None


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Client with authentication bypassed — for supplier/incident tests."""
    main = _build_app(monkeypatch, tmp_path)

    from auth.dependencies import get_current_user
    from users.models import UserResponse
    from datetime import datetime, timezone

    main.app.dependency_overrides[get_current_user] = lambda: UserResponse(
        id=1,
        email="tester@brasaland.com",
        name="Tester",
        is_active=True,
        is_admin=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()

    import database

    database._db = None
    database._users_db = None
    database._auth_db = None


@pytest.fixture()
def auth_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Client carrying a real bearer token for a freshly registered user."""
    main = _build_app(monkeypatch, tmp_path)
    with TestClient(main.app) as test_client:
        test_client.post(
            "/auth/register",
            json={"email": "user@brasaland.com", "password": "supersecret"},
        )
        token = test_client.post(
            "/auth/login",
            data={"username": "user@brasaland.com", "password": "supersecret"},
        ).json()["access_token"]
        test_client.headers["Authorization"] = f"Bearer {token}"
        yield test_client

    import database

    database._db = None
    database._users_db = None
    database._auth_db = None
