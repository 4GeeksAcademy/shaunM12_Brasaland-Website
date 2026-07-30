"""Unit tests for rule-based Support Agent classifier (P2-1 gate)."""

from __future__ import annotations

import pytest

from agent.classify import classify_question


@pytest.mark.parametrize(
    ("question", "expected_intent"),
    [
        ("How many points for Gold tier?", "rag"),
        ("List open incidents", "incident"),
        ("What is incident 42?", "incident"),
        ("Open incidents at Miami Doral", "incident"),
        ("Show internal origin incidents in progress", "incident"),
        ("Current stock for SKU BEEF-001", "inventory"),
        ("Open incidents and our waste disposal policy", "both"),
        ("Incident 12 and allergen manual", "both"),
        ("Stock levels and open tickets", "incident"),
        ("What's the weather?", "rag"),
    ],
)
def test_classify_intent_examples(question: str, expected_intent: str):
    result = classify_question(question)
    assert result.intent == expected_intent


def test_classify_extracts_incident_id():
    result = classify_question("What is incident 42?")
    assert result.incident_id == 42


def test_classify_hash_id_with_incident_context():
    result = classify_question("Status of #99 for open incidents")
    assert result.incident_id == 99


def test_classify_list_filters_without_id():
    result = classify_question("Open incidents at Miami Doral")
    assert result.incident_id is None
    assert result.incident_filters.get("status") == "open"
    assert result.incident_filters.get("branch") == "miami_doral"


def test_classify_trace_fields_present():
    result = classify_question("List open incidents")
    assert result.matched
    assert "incident" in result.matched or any("incident" in m for m in result.matched)


def test_classify_generic_problem_alone_is_rag():
    result = classify_question("I have a problem with my order")
    assert result.intent == "rag"
