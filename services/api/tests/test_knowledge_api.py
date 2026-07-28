"""Phase 3 knowledge API wiring tests (mocked RAG — no live Qdrant/LLM)."""

from __future__ import annotations

import importlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _build_knowledge_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Build app with Postgres disabled so lifespan does not need Supabase."""
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SUPPLIERS_DB_PATH", str(tmp_path / "suppliers.json"))
    monkeypatch.setenv("USERS_DB_PATH", str(tmp_path / "users.json"))
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "auth.json"))

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
def knowledge_anon_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    main = _build_knowledge_app(monkeypatch, tmp_path)
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture()
def knowledge_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    main = _build_knowledge_app(monkeypatch, tmp_path)
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


def test_knowledge_routes_require_auth(knowledge_anon_client):
    assert (
        knowledge_anon_client.post(
            "/knowledge/query", json={"question": "Gold tier?"}
        ).status_code
        == 401
    )
    assert knowledge_anon_client.post("/knowledge/reindex").status_code == 401


def test_knowledge_query_returns_answer_only(knowledge_client, monkeypatch):
    monkeypatch.setattr(
        "knowledge.routes.ensure_repo_root_on_path",
        lambda: None,
    )

    def _fake_query(question: str) -> str:
        assert "Gold" in question
        return "Gold requires 50+ points."

    import sys
    import types

    fake_pipelines = types.ModuleType("data.pipelines.rag")
    fake_pipelines.query = _fake_query
    monkeypatch.setitem(sys.modules, "data.pipelines.rag", fake_pipelines)
    if "data" not in sys.modules:
        sys.modules["data"] = types.ModuleType("data")
    if "data.pipelines" not in sys.modules:
        sys.modules["data.pipelines"] = types.ModuleType("data.pipelines")

    response = knowledge_client.post(
        "/knowledge/query",
        json={"question": "How many points for Gold?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {"answer": "Gold requires 50+ points."}
    assert set(body.keys()) == {"answer"}


def test_knowledge_query_rejects_blank_question(knowledge_client):
    response = knowledge_client.post("/knowledge/query", json={"question": "   "})
    assert response.status_code == 400


def test_knowledge_reindex_returns_status(knowledge_client, monkeypatch):
    monkeypatch.setattr(
        "knowledge.routes.ensure_repo_root_on_path",
        lambda: None,
    )

    import sys
    import types

    fake_process = types.ModuleType("data.process.rag")
    fake_process.setup = lambda dry_run=False: 14
    monkeypatch.setitem(sys.modules, "data.process.rag", fake_process)
    if "data" not in sys.modules:
        sys.modules["data"] = types.ModuleType("data")
    if "data.process" not in sys.modules:
        sys.modules["data.process"] = types.ModuleType("data.process")

    response = knowledge_client.post("/knowledge/reindex")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["chunks_indexed"] == 14
