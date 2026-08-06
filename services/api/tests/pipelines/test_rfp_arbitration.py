"""Unit tests for P3 arbitration helpers (context-27 P3 Phase 1)."""

from __future__ import annotations

from rfp.constants import (
    DEPARTMENT_MARKETING,
    DEPARTMENT_OPERATIONS,
    DEPARTMENT_PROCUREMENT,
    MAX_ARBITRATION_ITERATIONS,
)

from data.pipelines.rfp_arbitration import (
    RULE_MARKETING_PREFERENCE,
    RULE_STRICTEST_OPERATIONAL,
    RULE_UNRESOLVED,
    arbitrate_conflict,
    collect_conflicts,
    detect_draft_conflicts,
    run_arbitration,
)


def test_arbitrate_deadline_picks_later_date_strictest_operational():
    conflict = {
        "field": "deadline",
        "claims": [
            {"department_id": DEPARTMENT_MARKETING, "value": "2026-09-01"},
            {"department_id": DEPARTMENT_OPERATIONS, "value": "2026-09-15"},
        ],
    }
    result = arbitrate_conflict(conflict, iteration=1)
    assert result["winning_department_id"] == DEPARTMENT_OPERATIONS
    assert result["resolved_value"] == "2026-09-15"
    assert result["rule_id"] == RULE_STRICTEST_OPERATIONAL


def test_arbitrate_validity_days_marketing_wins():
    conflict = {
        "field": "validity_days",
        "claims": [
            {"department_id": DEPARTMENT_MARKETING, "value": "30"},
            {"department_id": DEPARTMENT_OPERATIONS, "value": "45"},
        ],
    }
    result = arbitrate_conflict(conflict, iteration=1)
    assert result["winning_department_id"] == DEPARTMENT_MARKETING
    assert result["rule_id"] == RULE_MARKETING_PREFERENCE


def test_detect_draft_conflicts_lead_time_mismatch():
    drafts = {
        DEPARTMENT_OPERATIONS: "Setup requires 12 business days for kitchen prep.",
        DEPARTMENT_PROCUREMENT: "Supplier delivery setup in 18 business days.",
    }
    conflicts = detect_draft_conflicts(drafts)
    assert len(conflicts) == 1
    assert conflicts[0]["field"] == "lead_time_business_days"
    assert len(conflicts[0]["claims"]) == 2


def test_collect_conflicts_merges_intake_and_draft_scan():
    intake = [
        {
            "field": "deadline",
            "claims": [
                {"department_id": DEPARTMENT_MARKETING, "value": "2026-09-01"},
                {"department_id": DEPARTMENT_OPERATIONS, "value": "2026-09-15"},
            ],
        }
    ]
    drafts = {
        DEPARTMENT_OPERATIONS: "Setup in 12 business days.",
        DEPARTMENT_PROCUREMENT: "Delivery setup in 20 business days.",
    }
    merged = collect_conflicts(intake_conflicts=intake, approved_drafts=drafts)
    fields = {c["field"] for c in merged}
    assert "deadline" in fields
    assert "lead_time_business_days" in fields


def test_run_arbitration_resolves_injected_intake_conflict():
    conflicts = [
        {
            "field": "deadline",
            "claims": [
                {"department_id": DEPARTMENT_MARKETING, "value": "2026-09-01"},
                {"department_id": DEPARTMENT_OPERATIONS, "value": "2026-09-15"},
            ],
        }
    ]
    outcome = run_arbitration(conflicts)
    assert len(outcome.resolutions) == 1
    assert not outcome.arbitration_exhausted
    assert outcome.remaining_conflicts == []


def test_run_arbitration_exhausted_on_unresolvable_conflict():
    conflicts = [
        {
            "field": "unknown_metric",
            "claims": [
                {"department_id": DEPARTMENT_MARKETING, "value": "alpha"},
                {"department_id": DEPARTMENT_OPERATIONS, "value": "beta"},
            ],
        }
    ]
    outcome = run_arbitration(conflicts, max_iterations=MAX_ARBITRATION_ITERATIONS)
    assert outcome.arbitration_exhausted is True
    assert len(outcome.remaining_conflicts) == 1
    assert outcome.rounds_used == MAX_ARBITRATION_ITERATIONS


def test_unresolvable_conflict_marks_rule_unresolved():
    conflict = {
        "field": "custom_field",
        "claims": [
            {"department_id": DEPARTMENT_MARKETING, "value": "a"},
            {"department_id": DEPARTMENT_PROCUREMENT, "value": "b"},
        ],
    }
    result = arbitrate_conflict(conflict, iteration=1)
    assert result["rule_id"] == RULE_UNRESOLVED
    assert result.get("unresolved") is True
