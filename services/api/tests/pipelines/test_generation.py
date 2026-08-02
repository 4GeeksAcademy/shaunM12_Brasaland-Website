"""Unit tests for Support Agent generation (P2-L35)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent.generation import (
    SUPPORT_SYSTEM_PROMPT,
    build_combined_context,
    generate_support_answer,
    knowledge_system_prompt_for_tests,
)


def test_build_combined_context_tool_only():
    tool_results = [
        {
            "source": "incidents_api",
            "ok": True,
            "rows": [
                {
                    "id": 1,
                    "title": "Oven fault",
                    "status": "open",
                    "origin": "branch",
                    "branch": "miami_doral",
                    "category": "equipment_failure",
                    "description": "Not heating",
                }
            ],
        }
    ]
    context = build_combined_context(tool_results=tool_results)
    assert "## Live operational data (incidents)" in context
    assert "scope=incidents" in context
    assert "Incident #1" in context
    assert "Knowledge base" not in context


def test_build_combined_context_inventory_tool():
    context = build_combined_context(
        tool_results=[
            {
                "source": "inventory_api",
                "ok": True,
                "rows": [
                    {
                        "id": 3,
                        "name": "Beef brisket",
                        "sku": "BRS-BEEF-001",
                        "unit": "kg",
                        "category": "meat",
                        "country": "CO",
                        "current_stock": 50.0,
                        "min_stock_threshold": 40.0,
                    }
                ],
            }
        ]
    )
    assert "## Live operational data (inventory)" in context
    assert "scope=inventory" in context
    assert "BRS-BEEF-001" in context
    assert "current_stock=50.0" in context


def test_build_combined_context_both_sources():
    context = build_combined_context(
        rag_context="[1] source=manual.md | section=Policy\nWaste rules apply.",
        tool_results=[
            {
                "source": "incidents_api",
                "ok": True,
                "rows": [{"id": 2, "title": "T", "status": "open", "origin": "internal", "branch": "central", "category": "other", "description": "d"}],
            }
        ],
    )
    assert "Live operational data" in context
    assert "## Knowledge base" in context
    assert "Waste rules" in context


def test_build_combined_context_caveat_prepended():
    context = build_combined_context(
        rag_context="KB only",
        caveat="Note: live incident lookup failed.",
    )
    assert context.startswith("Note: live incident lookup failed.")
    assert "Knowledge base" in context


def test_generate_support_answer_uses_support_prompt(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    class _FakeMessage:
        content = "Support summary of incidents."

    class _FakeChoice:
        message = _FakeMessage()

    class _FakeResponse:
        choices = [_FakeChoice()]

    class _FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _FakeResponse()

    class _FakeClient:
        chat = MagicMock(completions=_FakeCompletions())

    monkeypatch.setattr("agent.generation._load_env", lambda: None)
    monkeypatch.setattr(
        "agent.generation._generation_settings",
        lambda: ("http://gen.test", "key", "test-model"),
    )
    monkeypatch.setattr("agent.generation.generation_client", lambda: _FakeClient())

    answer = generate_support_answer(
        "List open incidents",
        tool_results=[
            {
                "source": "incidents_api",
                "ok": True,
                "rows": [
                    {
                        "id": 5,
                        "title": "Complaint",
                        "status": "open",
                        "origin": "customer",
                        "branch": "miami_doral",
                        "category": "customer_complaint",
                        "description": "Slow order",
                    }
                ],
            }
        ],
    )

    assert answer == "Support summary of incidents."
    messages = captured["messages"]
    assert messages[0]["content"] == SUPPORT_SYSTEM_PROMPT
    assert messages[0]["content"] != knowledge_system_prompt_for_tests()
    assert "Operational data" in messages[1]["content"] or "Live operational" in messages[1]["content"]
    assert captured["model"] == "test-model"
    assert captured["temperature"] == 0.2


def test_generate_support_answer_requires_context():
    with pytest.raises(ValueError, match="non-empty combined context"):
        generate_support_answer("incidents?", tool_results=[])
