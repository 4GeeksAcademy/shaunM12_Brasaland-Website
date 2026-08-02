"""Structured generation tests for Support Agent memory (context-26 P26-2)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from agent.generation import (
    build_combined_context,
    generate_structured_rag_response,
    generate_structured_support_response,
)
from agent.guardrails.prompts import support_system_prompt_with_memory
from agent.memory.structured_generation import build_generation_result


def test_build_generation_result_parses_valid_json():
    raw = json.dumps(
        {
            "answer": "Medellín supplier delivers on Wednesdays. Want me to remember that?",
            "memory_proposal": {
                "location_id": 3,
                "category": "suppliers",
                "key": "meat_delivery_day",
                "value": "Meat supplier delivers on Wednesdays",
                "reason": "User corrected recurring delivery day",
            },
        }
    )
    result = build_generation_result(raw)
    assert "Wednesdays" in result.answer
    assert result.memory_proposal is not None
    assert result.memory_proposal.key == "meat_delivery_day"
    assert result.proposal_trace is None


def test_build_generation_result_null_proposal():
    raw = json.dumps({"answer": "Gold tier requires 50 points.", "memory_proposal": None})
    result = build_generation_result(raw)
    assert result.memory_proposal is None


def test_build_generation_result_empty_answer_does_not_leak_raw_json():
    raw = '{"":":",""}'
    result = build_generation_result(raw)
    assert result.answer == "I couldn't return that response safely."
    assert "{" not in result.answer
    assert result.proposal_trace == "parse_failed"


def test_build_generation_result_empty_answer_field_uses_safe_fallback():
    raw = json.dumps({"answer": "", "memory_proposal": None})
    result = build_generation_result(raw)
    assert result.answer == "I couldn't return that response safely."
    assert result.memory_proposal is None


def test_build_generation_result_parse_failure_uses_raw_text():
    result = build_generation_result("Plain fallback answer.")
    assert result.answer == "Plain fallback answer."
    assert result.memory_proposal is None
    assert result.proposal_trace == "parse_failed"


def test_build_generation_result_validation_failure():
    raw = json.dumps(
        {
            "answer": "Remember payroll rules?",
            "memory_proposal": {
                "location_id": 3,
                "category": "suppliers",
                "key": "meat_delivery_day",
                "value": "Payroll is 5000 for Carlos",
            },
        }
    )
    result = build_generation_result(raw)
    assert result.memory_proposal is None
    assert result.proposal_trace == "validation_failed:payroll"


def test_build_generation_result_suppressed_when_pending():
    raw = json.dumps(
        {
            "answer": "Ok.",
            "memory_proposal": {
                "location_id": 3,
                "category": "suppliers",
                "key": "meat_delivery_day",
                "value": "Meat supplier delivers on Wednesdays",
            },
        }
    )
    result = build_generation_result(raw, allow_proposal=False)
    assert result.memory_proposal is None
    assert result.proposal_trace == "suppressed_pending"


def test_build_combined_context_includes_memory_block():
    combined = build_combined_context(
        rag_context="Gold requires 50 points.",
        memory_context="- [location_id=3 category=suppliers key=meat_delivery_day] Delivers Wednesdays",
    )
    assert "Approved operational memory" in combined
    assert "Knowledge base" in combined
    assert "Delivers Wednesdays" in combined


def test_generate_structured_support_response_mock_llm(monkeypatch: pytest.MonkeyPatch):
    payload = json.dumps(
        {
            "answer": "Stock looks fine.",
            "memory_proposal": None,
        }
    )

    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=payload))]
    mock_client.chat.completions.create.return_value = mock_completion

    monkeypatch.setattr("agent.generation.generation_client", lambda: mock_client)
    monkeypatch.setattr(
        "agent.generation._generation_settings",
        lambda: ("http://test", "key", "test-model"),
    )
    monkeypatch.setattr("agent.generation._load_env", lambda: None)

    tool_results = [
        {
            "source": "inventory_api",
            "ok": True,
            "rows": [
                {
                    "id": 1,
                    "name": "Beef",
                    "sku": "BEEF-001",
                    "current_stock": 10,
                    "unit": "kg",
                    "min_stock_threshold": 2,
                    "category": "meat",
                    "country": "CO",
                    "location_id": 4,
                }
            ],
        }
    ]

    result = generate_structured_support_response(
        "Stock for beef at Chapinero",
        tool_results=tool_results,
    )
    assert result.answer == "Stock looks fine."
    assert result.memory_proposal is None

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}
    system_content = call_kwargs["messages"][0]["content"]
    assert "Memory self-evaluation" in system_content


def test_generate_structured_rag_response_mock_llm(monkeypatch: pytest.MonkeyPatch):
    payload = json.dumps({"answer": "Gold requires 50 points.", "memory_proposal": None})
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=payload))]
    mock_client.chat.completions.create.return_value = mock_completion

    monkeypatch.setattr("agent.generation.generation_client", lambda: mock_client)
    monkeypatch.setattr(
        "agent.generation._generation_settings",
        lambda: ("http://test", "key", "test-model"),
    )
    monkeypatch.setattr("agent.generation._load_env", lambda: None)

    result = generate_structured_rag_response(
        "How many points for Gold tier?",
        "## Untrusted retrieved documents\nGold requires 50+ points.",
        memory_context="- [user_preference category=preferences key=report_format] Bullet points",
    )
    assert "50" in result.answer
    user_content = mock_client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "Approved operational memory" in user_content


def test_support_system_prompt_with_memory_includes_self_eval():
    prompt = support_system_prompt_with_memory()
    assert "Memory self-evaluation" in prompt
    assert "memory_proposal" in prompt
