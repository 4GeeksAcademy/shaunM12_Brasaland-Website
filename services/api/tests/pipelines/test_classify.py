"""Unit tests for rule-based Support Agent classifier (P2-1, P24-3b)."""

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
        ("How do I create an incident", "rag"),
        ("how do you create an incident?", "rag"),
        ("How can I log an incident", "rag"),
        ("Status of #42", "incident"),
        ("How many open incidents are there?", "incident"),
        (
            "Create incident for broken POS at Miami Doral: terminal frozen during lunch rush",
            "incident_write",
        ),
        ("Mark incident 42 as resolved", "incident_write"),
        ("Update #55 to in progress", "incident_write"),
        ("Restock SKU BEEF-001 at location 1", "inventory_write"),
        ("Submit inbound order for beef", "inventory_write"),
    ],
)
def test_classify_intent_examples(question: str, expected_intent: str):
    result = classify_question(question)
    assert result.intent == expected_intent


def test_classify_extracts_incident_id():
    result = classify_question("What is incident 42?")
    assert result.incident_id == 42


def test_classify_hash_id_relaxed_without_incident_noun():
    result = classify_question("Status of #42")
    assert result.incident_id == 42
    assert result.intent == "incident"


def test_classify_hash_id_with_incident_context():
    result = classify_question("Status of #99 for open incidents")
    assert result.incident_id == 99


def test_classify_list_filters_without_id():
    result = classify_question("Open incidents at Miami Doral")
    assert result.incident_id is None
    assert result.incident_filters.get("status") == "open"
    assert result.incident_filters.get("branch") == "miami_doral"


def test_classify_category_filter():
    result = classify_question("Open customer complaint incidents at Miami Doral")
    assert result.incident_filters.get("category") == "customer_complaint"
    assert result.incident_filters.get("branch") == "miami_doral"


def test_classify_summary_action():
    result = classify_question("How many open incidents are there?")
    assert result.intent == "incident"
    assert result.incident_action == "summary"


def test_classify_write_create_payload():
    result = classify_question(
        "Create incident for equipment failure at Miami Doral: oven not heating"
    )
    assert result.intent == "incident_write"
    assert result.write_action == "create"
    assert result.write_payload is not None
    assert result.write_payload["branch"] == "miami_doral"
    assert result.write_payload["category"] == "equipment_failure"
    assert result.write_payload["title"] == "Equipment failure"
    assert result.write_payload["description"] == "oven not heating"


def test_classify_write_create_pos_title():
    result = classify_question(
        "Create incident for broken POS at Miami Doral: terminal frozen during lunch rush"
    )
    assert result.write_payload is not None
    assert result.write_payload["title"] == "Broken POS"
    assert "terminal frozen" in result.write_payload["description"]


def test_classify_write_update_status():
    result = classify_question("Mark incident 42 as resolved")
    assert result.intent == "incident_write"
    assert result.write_action == "update_status"
    assert result.incident_id == 42
    assert result.write_status == "resolved"


def test_classify_trace_fields_present():
    result = classify_question("List open incidents")
    assert result.matched
    assert "incident" in result.matched or any("incident" in m for m in result.matched)


def test_classify_how_do_you_list_incidents_stays_live():
    result = classify_question("how do you list open incidents at Miami Doral")
    assert result.intent == "incident"
    assert result.incident_filters.get("branch") == "miami_doral"


def test_classify_instructive_create_matches_procedure_guard():
    result = classify_question("how do you create an incident?")
    assert result.intent == "rag"
    assert "procedure_guard:instructive_incident" in result.matched


def test_classify_generic_problem_alone_is_rag():
    result = classify_question("I have a problem with my order")
    assert result.intent == "rag"


def test_classify_show_me_all_incidents():
    result = classify_question("show me all incidents")
    assert result.intent == "incident"
    assert result.incident_id is None
    assert "status" not in result.incident_filters


def test_classify_plural_incidents_noun():
    result = classify_question("What incidents are open at Miami Doral?")
    assert result.intent == "incident"


def test_classify_list_incidents_defaults_open_status():
    result = classify_question("List incidents at Miami Doral")
    assert result.intent == "incident"
    assert result.incident_filters.get("status") == "open"
    assert result.incident_filters.get("branch") == "miami_doral"


def test_classify_how_much_beef_routes_inventory():
    result = classify_question("How much beef do we have")
    assert result.intent == "inventory"
    assert "inventory:hints" in result.matched
