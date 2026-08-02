"""Unit tests for memory proposal classifier (context-26 P26-L9)."""

from __future__ import annotations

from agent.memory.proposal import (
    classify_memory_decision,
    extract_continued_question,
    is_bare_assent,
    pending_is_expired,
)
from agent.memory.constants import (
    MEMORY_REJECT_BARE_ASSENT_MESSAGE,
    MEMORY_REJECT_USER_DECLINED_MESSAGE,
    memory_reject_message,
)


def test_bare_yes_is_ambiguous():
    result = classify_memory_decision("yes")
    assert result.outcome == "ambiguous"
    assert result.reason == "bare_assent"


def test_reject_declines_memory():
    result = classify_memory_decision("No, don't remember that")
    assert result.outcome == "reject"


def test_approve_with_memory_intent():
    result = classify_memory_decision("Yes, please remember that")
    assert result.outcome == "approve"
    assert result.continued_question is None


def test_approve_and_continue_same_message():
    result = classify_memory_decision("Yes, remember that — list open incidents")
    assert result.outcome == "approve"
    assert result.continued_question == "list open incidents"


def test_edit_extracts_value():
    result = classify_memory_decision("Remember it as delivers on Thursdays")
    assert result.outcome == "edit"
    assert result.edited_value == "delivers on Thursdays"


def test_extract_continued_question_strips_prefix():
    assert extract_continued_question("Yes remember that - show incidents") == "show incidents"


def test_pending_is_expired_after_ttl():
    from datetime import datetime, timedelta, timezone

    old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    assert pending_is_expired(old) is True


def test_is_bare_assent_recognizes_ok():
    assert is_bare_assent("OK") is True


def test_empty_reply_is_ambiguous():
    result = classify_memory_decision("")
    assert result.outcome == "ambiguous"
    assert result.reason == "empty_reply"


def test_reject_wins_over_edit_phrasing():
    result = classify_memory_decision("No, remember it as Thursdays")
    assert result.outcome == "reject"


def test_topic_change_while_pending_is_ambiguous():
    result = classify_memory_decision("List open incidents at Miami Doral")
    assert result.outcome == "ambiguous"
    assert result.reason == "topic_change"


def test_new_correction_supersedes_pending():
    from agent.memory.proposal import (
        ProposalResolution,
        should_continue_after_ambiguous_pending_resolution,
    )

    resolution = ProposalResolution(outcome="ambiguous", reason="no_memory_intent")
    question = "Jacksonville supplier deliveries are on Thursdays, not Wednesdays."
    assert should_continue_after_ambiguous_pending_resolution(resolution, question) is True


def test_topic_change_should_continue_graph():
    from agent.memory.proposal import (
        ProposalResolution,
        should_continue_after_ambiguous_pending_resolution,
    )

    resolution = ProposalResolution(outcome="ambiguous", reason="topic_change")
    assert should_continue_after_ambiguous_pending_resolution(
        resolution,
        "List open incidents at Miami Doral",
    ) is True


def test_spanish_approve_with_memory_intent():
    result = classify_memory_decision("Sí, recuerda eso")
    assert result.outcome == "approve"


def test_spanish_reject():
    result = classify_memory_decision("No, no lo guardes")
    assert result.outcome == "reject"


def test_memory_reject_message_for_bare_assent():
    message = memory_reject_message(outcome="ambiguous", reason="bare_assent")
    assert message == MEMORY_REJECT_BARE_ASSENT_MESSAGE
    assert "Yes, please remember that" in message


def test_memory_reject_message_for_denylist():
    from agent.memory.constants import MEMORY_REJECT_DENYLIST_MESSAGE

    message = memory_reject_message(outcome="reject", reason="payroll")
    assert message == MEMORY_REJECT_DENYLIST_MESSAGE


def test_memory_reject_message_for_user_declined():
    message = memory_reject_message(outcome="reject", reason="user_declined")
    assert message == MEMORY_REJECT_USER_DECLINED_MESSAGE

