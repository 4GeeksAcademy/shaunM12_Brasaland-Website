"""Location and key normalization tests for agent memory (all locations)."""

from __future__ import annotations

import json

import pytest

from agent.memory.keys import MemoryKeyError, validate_key
from agent.memory.location_hint import (
    build_location_disambiguation_message,
    reconcile_proposal_location_id,
)
from agent.memory.schemas import validate_proposal_shape
from agent.memory.store import filter_entries_for_location
from agent.memory.models import AgentMemoryEntry
from agent.memory.structured_generation import build_generation_result
from packages.shared.restaurant_locations import resolve_location_hint, resolve_location_scope


@pytest.mark.parametrize(
    ("raw_key", "expected"),
    [
        ("chapinero_vegetable_delivery_day", "vegetable_delivery_day"),
        ("medellin_meat_delivery_day", "meat_delivery_day"),
        ("envigado_meat_delivery_day", "meat_delivery_day"),
        ("miami_beach_weekend_close", "weekend_close"),
        ("tampa_general_delivery_day", "general_delivery_day"),
    ],
)
def test_normalize_key_strips_location_prefix(raw_key: str, expected: str):
    category = "suppliers" if "delivery" in expected else "hours"
    assert validate_key(category, raw_key) == expected


def test_validate_key_still_rejects_unknown():
    with pytest.raises(MemoryKeyError):
        validate_key("suppliers", "unknown_delivery")


@pytest.mark.parametrize(
    ("question", "expected_id"),
    [
        ("At Chapinero vegetable deliveries on Friday", 4),
        ("Miami Beach closes at 11pm on weekends", 8),
        ("Brickell weekend hours", 9),
        ("Tampa Bay meat supplier", 12),
        ("Jacksonville delivery schedule", 14),
        ("Cali Granada supplier order", 6),
        ("Barranquilla Norte deliveries", 7),
        ("Envigado meat supplier", 3),
        ("Laureles closing time", 2),
    ],
)
def test_resolve_location_hint_all_sites(question: str, expected_id: int):
    assert resolve_location_hint(question) == expected_id


def test_ambiguous_shared_city_does_not_pick_arbitrary_branch():
    assert resolve_location_hint("Operations update for Bogotá region") is None
    scope = resolve_location_scope("Operations update for Bogotá region")
    assert scope.is_ambiguous
    assert scope.ambiguous_ids == (4, 5)


def test_medellin_metro_is_ambiguous_without_neighborhood():
    scope = resolve_location_scope("Supplier delivery at Medellín")
    assert scope.is_ambiguous
    assert scope.ambiguous_ids == (1, 2, 3)


def test_disambiguation_message_lists_branches():
    message = build_location_disambiguation_message((1, 2, 3))
    assert "Centro" in message
    assert "Laureles" in message
    assert "Envigado" in message


def test_reconcile_uses_tampa_bay_without_user_typing_id():
    location_id = reconcile_proposal_location_id(
        None,
        "At Tampa Bay meat delivers on Wednesday. Remember that.",
        category="suppliers",
    )
    assert location_id == 12


def test_filter_entries_for_location_drops_other_sites():
    rows = [
        AgentMemoryEntry(
            id=1,
            location_id=3,
            user_id=None,
            category="suppliers",
            key="meat_delivery_day",
            value="Wed",
            approved_by=1,
        ),
        AgentMemoryEntry(
            id=2,
            location_id=12,
            user_id=None,
            category="suppliers",
            key="meat_delivery_day",
            value="Wed",
            approved_by=1,
        ),
    ]
    filtered = filter_entries_for_location(rows, 12)
    assert len(filtered) == 1
    assert filtered[0].location_id == 12


def test_validate_proposal_reconciles_envigado_over_wrong_llm_id():
    proposal = validate_proposal_shape(
        {
            "location_id": 1,
            "category": "suppliers",
            "key": "meat_delivery_day",
            "value": "Meat supplier delivers on Wednesdays",
        },
        question="At Envigado the meat supplier delivers on Wednesdays",
    )
    assert proposal.location_id == 3


def test_build_generation_result_normalizes_prefixed_key_without_http_error():
    raw = json.dumps(
        {
            "answer": "Chapinero vegetables deliver Friday. Want me to remember that?",
            "memory_proposal": {
                "location_id": 4,
                "category": "suppliers",
                "key": "chapinero_vegetable_delivery_day",
                "value": "Vegetable deliveries on Fridays",
            },
        }
    )
    result = build_generation_result(
        raw,
        question="At Chapinero vegetable deliveries come on Friday. Can you remember that?",
    )
    assert result.memory_proposal is not None
    assert result.memory_proposal.key == "vegetable_delivery_day"
    assert result.proposal_trace is None


def test_build_generation_result_invalid_key_returns_trace_not_exception():
    raw = json.dumps(
        {
            "answer": "Ok.",
            "memory_proposal": {
                "location_id": 4,
                "category": "suppliers",
                "key": "totally_unknown_key",
                "value": "Some fact",
            },
        }
    )
    result = build_generation_result(raw, question="At Chapinero note that")
    assert result.memory_proposal is None
    assert result.proposal_trace == "validation_failed:invalid_key"
