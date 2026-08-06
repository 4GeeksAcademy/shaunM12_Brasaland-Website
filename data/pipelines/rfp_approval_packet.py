"""P3 approval packet builders and human/CEO response guardrails (context-27 P3 M9-P3-16)."""

from __future__ import annotations

from typing import Any

from data.pipelines.rfp_intake import _ensure_repo_root_on_path

_ensure_repo_root_on_path()

from rfp.constants import (  # noqa: E402
    APPROVAL_DECISION_VALUES,
    CEO_DECISION_VALUES,
    department_label,
    department_owner,
)


class ApprovalResponseError(ValueError):
    """Raised when a human or CEO resume payload fails guardrail validation."""


def build_evaluation_summary(evaluation_results: dict[str, Any] | None) -> dict[str, Any]:
    """Derive compact evaluation summary from ``evaluation_results.latest``."""
    latest = (evaluation_results or {}).get("latest") or {}
    readability = latest.get("readability") or {}
    relevance = latest.get("relevance") or {}
    compliance = latest.get("compliance") or {}
    return {
        "iteration": latest.get("iteration"),
        "overall_passed": latest.get("overall_passed"),
        "needs_human_review": latest.get("needs_human_review"),
        "readability_passed": readability.get("passed"),
        "relevance_passed": relevance.get("passed"),
        "compliance_passed": compliance.get("passed"),
        "missing_topics": list(relevance.get("missing_topics") or []),
        "compliance_failures": list(compliance.get("failures") or []),
    }


def build_dept_approval_packet(
    *,
    ticket_id: str,
    department_id: str,
    metadata: dict[str, Any] | None,
    key_aspects: list[str] | None,
    draft_content: str | None,
    draft_status: str | None,
    evaluation_results: dict[str, Any] | None,
    requires_ceo_approval: bool,
    conflicts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Structured packet surfaced at department ``interrupt()`` (M9-P3-16)."""
    meta = metadata or {}
    packet: dict[str, Any] = {
        "ticket_id": ticket_id,
        "department_id": department_id,
        "department_label": department_label(department_id),
        "department_owner": department_owner(department_id),
        "client_name": meta.get("client_name"),
        "service_type": meta.get("service_type") or meta.get("scope"),
        "deadline": meta.get("deadline"),
        "key_aspects": list(key_aspects or []),
        "draft_content": draft_content or "",
        "draft_status": draft_status,
        "evaluation_summary": build_evaluation_summary(evaluation_results),
        "requires_ceo_approval": requires_ceo_approval,
    }
    if conflicts:
        packet["conflicts"] = list(conflicts)
    return packet


def build_ceo_approval_packet(
    *,
    ticket_id: str,
    metadata: dict[str, Any] | None,
    requires_ceo_approval: bool,
    approved_excerpts: dict[str, str],
    arbitration_resolutions: list[dict[str, Any]] | None,
    remaining_conflicts: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """CEO interrupt packet (M9-P3-11)."""
    meta = metadata or {}
    estimated = meta.get("estimated_contract_value_usd")
    threshold_reason = None
    if requires_ceo_approval and estimated is not None:
        threshold_reason = f"Estimated contract value ${estimated:,.0f} USD exceeds CEO threshold."

    excerpts: dict[str, str] = {}
    for dept, content in (approved_excerpts or {}).items():
        text = (content or "").strip()
        excerpts[dept] = text[:300] + ("…" if len(text) > 300 else "")

    return {
        "ticket_id": ticket_id,
        "kind": "ceo_approval",
        "client_name": meta.get("client_name"),
        "estimated_contract_value_usd": estimated,
        "threshold_reason": threshold_reason,
        "requires_ceo_approval": requires_ceo_approval,
        "approved_excerpts": excerpts,
        "arbitration_resolutions": list(arbitration_resolutions or []),
        "conflicts": list(remaining_conflicts or []),
    }


def validate_human_response(
    payload: dict[str, Any],
    *,
    expected_department_id: str,
) -> dict[str, Any]:
    """Guardrail for dept approval resume payload (M9-P3-6)."""
    if payload.get("kind") not in (None, "dept_approval"):
        raise ApprovalResponseError("Invalid interrupt kind for department approval.")

    department_id = str(payload.get("department_id") or "").strip()
    if department_id != expected_department_id:
        raise ApprovalResponseError(
            f"Department mismatch: expected '{expected_department_id}', got '{department_id}'."
        )

    decision = str(payload.get("decision") or "").strip()
    if decision not in APPROVAL_DECISION_VALUES:
        raise ApprovalResponseError(
            f"Invalid decision '{decision}'. Expected one of: {sorted(APPROVAL_DECISION_VALUES)}."
        )

    return {
        "kind": "dept_approval",
        "department_id": department_id,
        "decision": decision,
        "approver": str(payload.get("approver") or "Unknown").strip() or "Unknown",
        "comment": str(payload.get("comment") or "").strip(),
    }


def validate_ceo_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Guardrail for CEO approval resume payload (M9-P3-11)."""
    if payload.get("kind") not in (None, "ceo_approval"):
        raise ApprovalResponseError("Invalid interrupt kind for CEO approval.")

    decision = str(payload.get("decision") or "").strip()
    if decision not in CEO_DECISION_VALUES:
        raise ApprovalResponseError(
            f"Invalid CEO decision '{decision}'. Expected one of: {sorted(CEO_DECISION_VALUES)}."
        )

    return {
        "kind": "ceo_approval",
        "decision": decision,
        "approver": str(payload.get("approver") or "Mariana Restrepo").strip() or "Mariana Restrepo",
        "comment": str(payload.get("comment") or "").strip(),
    }


__all__ = [
    "ApprovalResponseError",
    "build_ceo_approval_packet",
    "build_dept_approval_packet",
    "build_evaluation_summary",
    "validate_ceo_response",
    "validate_human_response",
]
