"""Tests for memory correction intent helpers (context-26)."""

from __future__ import annotations

from agent.memory.correction_intent import (
    strip_memory_confirmation_ask,
    user_wants_memory_proposal,
)


def test_lookup_question_does_not_want_proposal():
    assert (
        user_wants_memory_proposal("When do vegetable deliveries arrive at Usaquén?")
        is False
    )


def test_correction_question_wants_proposal():
    assert (
        user_wants_memory_proposal(
            "Usaquén vegetable deliveries are on Fridays, not Thursdays."
        )
        is True
    )


def test_strip_memory_confirmation_ask_removes_trailing_prompt():
    answer = (
        "For Brasaland Bogotá Usaquén, vegetable deliveries arrive on Fridays. "
        "Would you like me to remember this for next time?"
    )
    stripped = strip_memory_confirmation_ask(answer)
    assert "remember" not in stripped.lower()
    assert "Fridays" in stripped
