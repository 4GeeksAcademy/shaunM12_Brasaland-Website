"""Support Agent API wiring tests (mocked graph — no live Qdrant/LLM)."""

from __future__ import annotations

import importlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _build_agent_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Build app with Postgres disabled so lifespan does not need Supabase."""
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SUPPLIERS_DB_PATH", str(tmp_path / "suppliers.json"))
    monkeypatch.setenv("USERS_DB_PATH", str(tmp_path / "users.json"))
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "auth.json"))
    monkeypatch.setenv("AGENT_CHECKPOINT_DB_PATH", str(tmp_path / "checkpoints.db"))

    import config

    monkeypatch.setattr(config, "DATABASE_URL", None)

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
def agent_anon_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    main = _build_agent_app(monkeypatch, tmp_path)
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture()
def agent_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    main = _build_agent_app(monkeypatch, tmp_path)
    from auth.dependencies import get_current_user
    from users.models import UserResponse

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


def test_agent_routes_require_auth(agent_anon_client):
    assert (
        agent_anon_client.post(
            "/agent/query", json={"question": "Gold tier?"}
        ).status_code
        == 401
    )


def test_agent_query_returns_answer_only(agent_client, monkeypatch):
    monkeypatch.setattr(
        "agent.routes.ensure_repo_root_on_path",
        lambda: None,
    )

    def _fake_invoke(question: str, *, thread_id=None):
        assert "Gold" in question
        return {
            "question": question,
            "chunks": [],
            "context_text": "",
            "answer": "Gold requires 50+ points.",
            "route": "generate",
            "error": None,
            "trace_events": [{"node": "generate"}],
        }

    monkeypatch.setattr("agent.routes.invoke_support_agent", _fake_invoke)

    response = agent_client.post(
        "/agent/query",
        json={"question": "How many points for Gold?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {"answer": "Gold requires 50+ points."}
    assert set(body.keys()) == {"answer"}


def test_agent_query_rejects_blank_question(agent_client):
    response = agent_client.post("/agent/query", json={"question": "   "})
    assert response.status_code == 400


def test_agent_query_returns_502_on_graph_failure(agent_client, monkeypatch):
    monkeypatch.setattr(
        "agent.routes.ensure_repo_root_on_path",
        lambda: None,
    )

    def _boom(_question: str, *, thread_id=None):
        raise RuntimeError("graph exploded")

    monkeypatch.setattr("agent.routes.invoke_support_agent", _boom)

    response = agent_client.post(
        "/agent/query",
        json={"question": "loyalty points"},
    )
    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Support Agent failed to answer. Try again shortly."
    )
