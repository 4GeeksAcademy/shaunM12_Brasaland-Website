"""Shared Support Agent trace assertions (context-25 P25-6)."""

from __future__ import annotations


def trace_nodes(state: dict) -> list[str]:
    return [event["node"] for event in state.get("trace_events", [])]


def assert_guardrail_prefix(nodes: list[str]) -> None:
    """Every classified path runs intake → guard_input → classify."""
    assert "intake" in nodes
    assert "guard_input" in nodes
    assert "classify" in nodes
    assert nodes.index("intake") < nodes.index("guard_input") < nodes.index("classify")


def assert_validate_after_generate(nodes: list[str]) -> None:
    """LLM generate paths terminate through validate_output."""
    assert "generate" in nodes
    assert "validate_output" in nodes
    assert nodes.index("generate") < nodes.index("validate_output")


def assert_no_validate_output(nodes: list[str]) -> None:
    assert "validate_output" not in nodes
