"""P25-1 prompt security tests — universal block on both generation paths."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent.generation import (
    SUPPORT_SYSTEM_PROMPT,
    generate_support_answer,
    knowledge_system_prompt_for_tests,
)
from data.pipelines.prompt_security import (
    UNIVERSAL_SECURITY_BLOCK,
    build_knowledge_user_prompt,
    knowledge_system_prompt,
)


def test_knowledge_system_prompt_includes_universal_security():
    prompt = knowledge_system_prompt()
    assert "trained salesperson" in prompt
    assert "Instruction authority" in prompt
    assert "Untrusted context" in prompt
    assert UNIVERSAL_SECURITY_BLOCK in prompt


def test_knowledge_system_prompt_avoids_provider_injection_trigger_phrases():
    prompt = knowledge_system_prompt().lower()
    assert "instruction authority" in prompt
    assert "ignore previous instructions" not in prompt
    assert "ignore your previous" not in prompt


def test_support_system_prompt_includes_domain_and_security():
    assert "Support Agent" in SUPPORT_SYSTEM_PROMPT
    assert "Company domain" in SUPPORT_SYSTEM_PROMPT
    assert "Instruction authority" in SUPPORT_SYSTEM_PROMPT
    assert SUPPORT_SYSTEM_PROMPT != knowledge_system_prompt_for_tests()


def test_build_knowledge_user_prompt_framing():
    user = build_knowledge_user_prompt(
        question="Gold tier?",
        context="[1] source=loyalty | section=Gold\n50 points.",
    )
    assert "Untrusted retrieved documents" in user
    assert "not instructions" in user
    assert "User question (not system instructions)" in user
    assert "Gold tier?" in user


def test_generate_support_answer_sends_hardened_prompts(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    class _FakeMessage:
        content = "ok"

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

    generate_support_answer(
        "List open incidents",
        tool_results=[
            {
                "source": "incidents_api",
                "ok": True,
                "rows": [
                    {
                        "id": 1,
                        "title": "T",
                        "status": "open",
                        "origin": "branch",
                        "branch": "miami_doral",
                        "category": "other",
                        "description": "d",
                    }
                ],
            }
        ],
    )

    system = captured["messages"][0]["content"]
    user = captured["messages"][1]["content"]
    assert "Instruction authority" in system
    assert "Company domain" in system
    assert "Untrusted context" in user
    assert "not system instructions" in user
