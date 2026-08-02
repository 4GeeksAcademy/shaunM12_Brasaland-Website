"""Tests for server-side memory proposal inference (context-26)."""

from __future__ import annotations

from agent.memory.proposal_inference import (
    answer_solicits_memory_confirmation,
    infer_memory_proposal,
    infer_validated_memory_proposal,
)


def test_answer_solicits_memory_confirmation_detects_update_prompt():
    answer = (
        "Would you like me to update the memory to reflect that the general "
        "supplier delivers on Thursday for Jacksonville?"
    )
    assert answer_solicits_memory_confirmation(answer) is True


def test_infer_jacksonville_general_delivery_correction():
    question = "Jacksonville supplier deliveries are on Thursdays, not Wednesdays."
    answer = (
        "Approved memory for Jacksonville (location_id=14) says Monday. "
        "Would you like me to update the memory to reflect Thursday deliveries?"
    )
    proposal = infer_memory_proposal(question, answer=answer)
    assert proposal is not None
    assert proposal.location_id == 14
    assert proposal.key == "general_delivery_day"
    assert "Thursday" in proposal.value


def test_infer_validated_proposal_passes_shape_checks():
    question = "Envigado meat supplier delivers on Wednesdays, not Tuesdays."
    answer = "Want me to remember that for next time?"
    validated = infer_validated_memory_proposal(question, answer=answer)
    assert validated is not None
    assert validated.key == "meat_delivery_day"
    assert validated.location_id == 3


def test_infer_from_correction_without_confirmation_phrase_in_answer():
    question = "Jacksonville supplier deliveries are on Thursdays, not Wednesdays."
    answer = "The approved memory says Monday; Thursday differs from that record."
    proposal = infer_memory_proposal(question, answer=answer)
    assert proposal is not None
    assert proposal.location_id == 14


def test_infer_returns_none_without_location():
    question = "Supplier deliveries are on Thursdays, not Wednesdays."
    answer = "Would you like me to remember that for next time?"
    assert infer_memory_proposal(question, answer=answer) is None


def test_infer_barranquilla_weekend_close_hours():
    question = "Barranquilla Norte weekend close is 11pm, not 10pm."
    answer = (
        "Weekend closing is 11 pm. Would you like me to remember this for next time?"
    )
    proposal = infer_validated_memory_proposal(question, answer=answer)
    assert proposal is not None
    assert proposal.location_id == 7
    assert proposal.category == "hours"
    assert proposal.key == "weekend_close"
    assert "11pm" in proposal.value.lower()
