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
def db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Throwaway TinyDB pointed at ``tmp_path``, with no app/HTTP layer.

    For the pure-function unit tests that import ``auth`` helpers directly. The
    auth modules resolve tables lazily via ``database.get_*_table()``, so
    reloading ``database`` and clearing its cached handles is enough to isolate
    each test from the real data files.
    """
    monkeypatch.setenv("SUPPLIERS_DB_PATH", str(tmp_path / "suppliers.json"))
    monkeypatch.setenv("USERS_DB_PATH", str(tmp_path / "users.json"))
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "auth.json"))

    import database

    importlib.reload(database)
    database._db = None
    database._users_db = None
    database._auth_db = None

    yield database

    database._db = None
    database._users_db = None
    database._auth_db = None


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


def _is_rfp_db_test(request: pytest.FixtureRequest) -> bool:
    module_name = getattr(request.module, "__name__", "") or ""
    return "rfp" in module_name.lower()


def _wait_for_rfp_background_tasks(*, timeout_seconds: float = 120.0) -> None:
    """Block until intake/draft/approval background workers finish (avoids delete races)."""
    import time

    from rfp.approval_service import _approval_lock, _approval_running
    from rfp.draft_service import _draft_lock, _draft_running
    from rfp.intake_service import _intake_lock, _intake_running

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with _draft_lock:
            draft_busy = bool(_draft_running)
        with _intake_lock:
            intake_busy = bool(_intake_running)
        with _approval_lock:
            approval_busy = bool(_approval_running)
        if not draft_busy and not intake_busy and not approval_busy:
            return
        time.sleep(0.05)


def _delete_rfp_tickets_not_in_baseline(baseline_ids: set[str]) -> None:
    import config

    if not config.DATABASE_URL:
        return

    from database import get_engine
    from rfp.repository import delete_ticket, list_tickets
    from sqlmodel import Session

    _wait_for_rfp_background_tasks()

    with Session(get_engine()) as session:
        for row in list_tickets(session, limit=1000):
            if row.ticket_id in baseline_ids:
                continue
            try:
                delete_ticket(session, row.ticket_id)
            except Exception:
                session.rollback()


@pytest.fixture(scope="session")
def _rfp_ticket_cleanup_session():
    """Snapshot RFP tickets at session start; delete test-created rows at session end."""
    import config

    if not config.DATABASE_URL:
        yield set()
        return

    from database import get_engine
    from rfp.repository import list_tickets
    from sqlmodel import Session

    with Session(get_engine()) as session:
        baseline_ids = {row.ticket_id for row in list_tickets(session, limit=1000)}

    yield baseline_ids

    _delete_rfp_tickets_not_in_baseline(baseline_ids)


@pytest.fixture(autouse=True)
def _rfp_ticket_cleanup_autouse(request: pytest.FixtureRequest, _rfp_ticket_cleanup_session):
    """Ensure session cleanup fixture is active for RFP DB test modules."""
    if not _is_rfp_db_test(request):
        yield
        return
    _wait_for_rfp_background_tasks()
    yield
    _wait_for_rfp_background_tasks()
