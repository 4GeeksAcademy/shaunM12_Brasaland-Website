"""Unit tests for Support Agent memory store (context-26 P26-1)."""

from __future__ import annotations

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from agent.memory.denylist import check_denylist
from agent.memory.keys import MemoryKeyError, validate_key
from agent.memory.models import AgentMemoryAuditLog, AgentMemoryEntry
from agent.memory.schemas import MemoryProposal, ProposalValidationError, validate_proposal_shape
from agent.memory.store import (
    cap_per_location,
    format_memory_context,
    log_proposal,
    read_memory,
    write_memory,
)


@pytest.fixture
def memory_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_MEMORY_CAP_PER_LOCATION", "12")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[AgentMemoryEntry.__table__, AgentMemoryAuditLog.__table__],
    )
    with Session(engine) as session:
        yield session


def test_validate_key_rejects_unknown_supplier_key():
    with pytest.raises(MemoryKeyError):
        validate_key("suppliers", "unknown_delivery")


def test_validate_proposal_shape_requires_location_for_suppliers():
    with pytest.raises(ProposalValidationError, match="location_id_required"):
        validate_proposal_shape(
            {
                "category": "suppliers",
                "key": "meat_delivery_day",
                "value": "Delivers on Wednesdays",
            }
        )


def test_denylist_blocks_payroll_and_zero_risk():
    payroll = check_denylist(
        category="hours",
        value="Carlos salary is 5000 USD",
    )
    assert payroll.blocked is True
    assert payroll.reason == "payroll"

    zero_risk = check_denylist(
        category="hours",
        value="Allergens are zero risk at this location",
    )
    assert zero_risk.blocked is True
    assert zero_risk.reason == "allergen_zero_risk"


def test_write_memory_upserts_same_key(memory_session: Session):
    proposal = {
        "location_id": 3,
        "category": "suppliers",
        "key": "meat_delivery_day",
        "value": "Meat supplier delivers on Tuesdays",
        "reason": "User correction",
    }
    first = write_memory(memory_session, proposal=proposal, approved_by=42)
    assert first.ok is True
    assert first.entry_id is not None

    updated = {
        **proposal,
        "value": "Meat supplier delivers on Wednesdays",
    }
    second = write_memory(memory_session, proposal=updated, approved_by=42)
    assert second.ok is True
    assert second.superseded_value == "Meat supplier delivers on Tuesdays"

    rows = read_memory(memory_session, location_id=3, user_id=42)
    assert len(rows) == 1
    assert rows[0].value == "Meat supplier delivers on Wednesdays"


def test_write_memory_rejects_denylist(memory_session: Session):
    result = write_memory(
        memory_session,
        proposal={
            "location_id": 4,
            "category": "suppliers",
            "key": "meat_delivery_day",
            "value": "Payroll for staff is confidential",
        },
        approved_by=7,
    )
    assert result.ok is False
    assert result.outcome == "rejected_denylist"

    rows = read_memory(memory_session, location_id=4, user_id=7)
    assert rows == []


def test_preferences_scoped_to_user(memory_session: Session):
    proposal = {
        "category": "preferences",
        "key": "report_format",
        "value": "Bullet points for incident summaries",
    }
    write_memory(memory_session, proposal=proposal, approved_by=10)
    write_memory(memory_session, proposal=proposal, approved_by=11)

    user_10 = read_memory(memory_session, user_id=10)
    user_11 = read_memory(memory_session, user_id=11)
    assert len(user_10) == 1
    assert len(user_11) == 1
    assert user_10[0].approved_by == 10
    assert user_11[0].approved_by == 11


def test_log_proposal_appends_audit_row(memory_session: Session):
    row = log_proposal(
        memory_session,
        user_id=5,
        outcome="rejected_ambiguous",
        proposal=MemoryProposal(
            location_id=1,
            category="hours",
            key="friday_close",
            value="Closes at 11pm on Fridays",
        ),
        reason="topic_change",
        user_message="List open incidents",
        thread_id="thread-abc",
    )
    assert row.id is not None
    assert row.outcome == "rejected_ambiguous"
    assert row.thread_id == "thread-abc"


def test_cap_per_location_blocks_new_keys(memory_session: Session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_MEMORY_CAP_PER_LOCATION", "2")
    location_id = 8
    keys = ("weekday_open", "weekday_close", "friday_close")
    for index, key in enumerate(keys):
        result = write_memory(
            memory_session,
            proposal={
                "location_id": location_id,
                "category": "hours",
                "key": key,
                "value": f"Hours fact {index}",
            },
            approved_by=99,
        )
        if index < 2:
            assert result.ok is True
        else:
            assert result.ok is False
            assert result.outcome == "rejected_cap_exceeded"


def test_format_memory_context_english_lines():
    entry = AgentMemoryEntry(
        id=1,
        location_id=3,
        user_id=None,
        category="suppliers",
        key="meat_delivery_day",
        value="Meat supplier delivers on Wednesdays",
        approved_by=1,
    )
    text = format_memory_context([entry])
    assert "location_id=3" in text
    assert "meat_delivery_day" in text
    assert "Wednesdays" in text


def test_cap_per_location_default():
    assert cap_per_location() == 12
