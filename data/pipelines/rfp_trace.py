"""RFP trace helpers — structured envelope for P1–P3 graph nodes (context-27 M9-P3-14)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# LangGraph node name → logical agent id (M9-P3-14 mapping table).
P1_AGENT_BY_NODE: dict[str, str] = {
    "convert_pdf": "pdf_converter",
    "readability": "readability_scorer",
    "classify": "rfp_classifier",
    "orchestrate": "intake_orchestrator",
    "worker": "department_worker",
    "synthesize": "intake_synthesizer",
    "pipeline_error": "pipeline_guardrail",
}

P2_AGENT_BY_NODE: dict[str, str] = {
    "draft_start": "draft_orchestrator",
    "generate_eval_dept": "department_generator",
    "generation_finalize": "draft_orchestrator",
    "pipeline_error": "pipeline_guardrail",
}

P3_AGENT_BY_NODE: dict[str, str] = {
    "approval_start": "approval_orchestrator",
    "prepare_approval_packet": "approval_orchestrator",
    "approval_join": "approval_orchestrator",
    "approval_finalize": "approval_orchestrator",
    "dept_approval_interrupt": "human_approval_gate",
    "validate_human_response": "approval_guardrail",
    "validate_ceo_response": "approval_guardrail",
    "mark_dept_approved": "approval_orchestrator",
    "mark_dept_rejected": "approval_orchestrator",
    "dept_regen": "department_generator",
    "detect_conflicts": "conflict_detector",
    "arbitration_node": "arbitration_node",
    "ceo_approval_interrupt": "ceo_approval_gate",
    "ultimate_document_synthesizer": "document_synthesizer",
}

AGENT_BY_NODE: dict[str, str] = {
    **P1_AGENT_BY_NODE,
    **P2_AGENT_BY_NODE,
    **P3_AGENT_BY_NODE,
}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def trace_node(
    node: str,
    *,
    agent: str | None = None,
    input_data: dict[str, Any] | None = None,
    output_data: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """Build one trace event for graph state and ``rfp_trace_events`` dual-write."""
    return [
        {
            "node": node,
            "agent": agent or AGENT_BY_NODE.get(node, node),
            "input": dict(input_data or {}),
            "output": dict(output_data or {}),
            "timestamp": timestamp or utc_timestamp(),
        }
    ]


def trace_p3(
    node: str,
    *,
    agent: str | None = None,
    input_data: dict[str, Any] | None = None,
    output_data: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """Alias for P3 nodes — same envelope as ``trace_node``."""
    return trace_node(
        node,
        agent=agent,
        input_data=input_data,
        output_data=output_data,
        timestamp=timestamp,
    )


def draft_trace_summary(draft_content: str | None, *, preview_chars: int = 200) -> dict[str, Any]:
    """Compact draft reference for trace input/output (avoid full text in trace rows)."""
    text = (draft_content or "").strip()
    preview = text[:preview_chars]
    if len(text) > preview_chars:
        preview = preview.rstrip() + "…"
    return {
        "draft_content_length": len(text),
        "draft_content_preview": preview,
    }


__all__ = [
    "AGENT_BY_NODE",
    "P1_AGENT_BY_NODE",
    "P2_AGENT_BY_NODE",
    "P3_AGENT_BY_NODE",
    "draft_trace_summary",
    "trace_node",
    "trace_p3",
    "utc_timestamp",
]
