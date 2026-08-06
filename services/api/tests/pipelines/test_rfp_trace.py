"""Unit tests for RFP trace helpers (context-27 P1–P3 M9-P3-14)."""

from __future__ import annotations

from data.pipelines.rfp_trace import (
    P1_AGENT_BY_NODE,
    P2_AGENT_BY_NODE,
    P3_AGENT_BY_NODE,
    draft_trace_summary,
    trace_node,
    trace_p3,
)


def _assert_trace_envelope(event: dict, *, node: str, agent: str) -> None:
    assert event["node"] == node
    assert event["agent"] == agent
    assert isinstance(event["input"], dict)
    assert isinstance(event["output"], dict)
    assert event["timestamp"].endswith("Z")


def test_trace_p3_envelope_has_required_fields():
    events = trace_p3(
        "dept_approval_interrupt",
        input_data={"department_id": "operations"},
        output_data={"status": "awaiting_human"},
    )
    assert len(events) == 1
    _assert_trace_envelope(
        events[0],
        node="dept_approval_interrupt",
        agent="human_approval_gate",
    )
    assert events[0]["input"]["department_id"] == "operations"
    assert events[0]["output"]["status"] == "awaiting_human"


def test_trace_p3_uses_agent_mapping():
    events = trace_p3("arbitration_node", input_data={}, output_data={})
    assert events[0]["agent"] == P3_AGENT_BY_NODE["arbitration_node"]


def test_trace_node_p1_envelope():
    events = trace_node(
        "convert_pdf",
        input_data={"pdf_path": "/tmp/sample.pdf"},
        output_data={"markdown_length": 1200},
    )
    _assert_trace_envelope(events[0], node="convert_pdf", agent=P1_AGENT_BY_NODE["convert_pdf"])
    assert events[0]["output"]["markdown_length"] == 1200


def test_trace_node_p2_envelope():
    events = trace_node(
        "generate_eval_dept",
        input_data={"department_id": "marketing"},
        output_data={"draft_status": "passed", "iteration": 1},
    )
    _assert_trace_envelope(
        events[0],
        node="generate_eval_dept",
        agent=P2_AGENT_BY_NODE["generate_eval_dept"],
    )


def test_draft_trace_summary_truncates_preview():
    long_draft = "x" * 500
    summary = draft_trace_summary(long_draft, preview_chars=200)
    assert summary["draft_content_length"] == 500
    assert summary["draft_content_preview"].endswith("…")
    assert len(summary["draft_content_preview"]) <= 201
