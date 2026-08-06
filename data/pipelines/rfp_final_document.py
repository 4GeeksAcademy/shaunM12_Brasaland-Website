"""P3 final document — deterministic merge of approved sections (context-27 P3 M9-P3-13)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from data.pipelines.rfp_intake import _ensure_repo_root_on_path

_ensure_repo_root_on_path()

from rfp.constants import (  # noqa: E402
    APPROVAL_STATUS_APPROVED,
    APPROVAL_STATUS_REJECTED,
    DEPARTMENT_MARKETING,
    DEPARTMENT_OPERATIONS,
    DEPARTMENT_PROCUREMENT,
    DEPARTMENT_TRAINING,
    department_label,
)

DEPARTMENT_SECTION_ORDER: tuple[str, ...] = (
    DEPARTMENT_MARKETING,
    DEPARTMENT_OPERATIONS,
    DEPARTMENT_PROCUREMENT,
    DEPARTMENT_TRAINING,
)

VALIDITY_FOOTER = (
    "Offer validity: 30 days from issuance (COMPLIANCE_VALIDITY_30_DAYS)."
)


class SynthesisGateError(ValueError):
    """Raised when ``build_final_document`` prerequisites are not met."""


@dataclass
class SectionSnapshot:
    department_id: str
    draft_content: str
    approval_status: str | None = None


@dataclass
class SynthesisContext:
    """Inputs for deterministic final document merge."""

    metadata: dict[str, Any] = field(default_factory=dict)
    intake_summary: str = ""
    departments_needed: list[str] = field(default_factory=list)
    sections: list[SectionSnapshot] = field(default_factory=list)
    arbitration_resolutions: list[dict[str, Any]] = field(default_factory=list)
    requires_ceo_approval: bool = False
    ceo_approved: bool = False
    arbitration_exhausted: bool = False


def validate_synthesis_gates(ctx: SynthesisContext) -> None:
    """Enforce M9-P3-13 hard prerequisites; raise ``SynthesisGateError`` on failure."""
    if ctx.arbitration_exhausted:
        raise SynthesisGateError("Arbitration exhausted — cannot synthesize final document.")

    active = set(ctx.departments_needed or [])
    if not active:
        raise SynthesisGateError("No departments_needed on ticket.")

    section_by_dept = {s.department_id: s for s in ctx.sections if s.department_id in active}

    for dept in active:
        section = section_by_dept.get(dept)
        if section is None:
            raise SynthesisGateError(f"Missing section row for department '{dept}'.")
        if section.approval_status == APPROVAL_STATUS_REJECTED:
            raise SynthesisGateError(f"Department '{dept}' is rejected.")
        if section.approval_status != APPROVAL_STATUS_APPROVED:
            raise SynthesisGateError(f"Department '{dept}' is not approved.")

    if ctx.requires_ceo_approval and not ctx.ceo_approved:
        raise SynthesisGateError("CEO approval required but not recorded.")


def can_synthesize(ctx: SynthesisContext) -> bool:
    try:
        validate_synthesis_gates(ctx)
        return True
    except SynthesisGateError:
        return False


def build_final_document(
    ctx: SynthesisContext,
    *,
    generated_at: datetime | None = None,
) -> str:
    """Deterministic markdown merge — not LLM (M9-P3-13)."""
    validate_synthesis_gates(ctx)

    when = generated_at or datetime.now(timezone.utc)
    meta = ctx.metadata or {}
    client = meta.get("client_name") or "Unknown client"
    service = meta.get("service_type") or meta.get("scope") or "Unspecified"
    location = meta.get("location") or "Unspecified"
    deadline = meta.get("deadline") or "Not specified"

    lines: list[str] = [
        f"# Brasaland Proposal — {client}",
        "",
        f"**Prepared for:** {client}  ",
        f"**Service:** {service}  ",
        f"**Location:** {location}  ",
        f"**Deadline:** {deadline}  ",
        f"**Generated:** {when.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "## Executive summary",
        "",
        (ctx.intake_summary or "").strip() or "_No intake summary available._",
        "",
        "## Department sections",
        "",
    ]

    section_by_dept = {s.department_id: s for s in ctx.sections}
    active = set(ctx.departments_needed or [])

    for dept in DEPARTMENT_SECTION_ORDER:
        if dept not in active:
            continue
        section = section_by_dept.get(dept)
        label = department_label(dept)
        lines.append(f"### {label}")
        lines.append("")
        content = (section.draft_content if section else "") or "_No content._"
        lines.append(content.strip())
        lines.append("")

    if ctx.arbitration_resolutions:
        lines.append("## Arbitration resolutions")
        lines.append("")
        for resolution in ctx.arbitration_resolutions:
            field_name = resolution.get("field", "unknown")
            winner = resolution.get("winning_department_id", "—")
            value = resolution.get("resolved_value", "—")
            rule_id = resolution.get("rule_id", "—")
            lines.append(
                f"- **{field_name}:** {value} (dept: {winner}, rule: {rule_id})"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(VALIDITY_FOOTER)

    return "\n".join(lines).strip() + "\n"


__all__ = [
    "DEPARTMENT_SECTION_ORDER",
    "SectionSnapshot",
    "SynthesisContext",
    "SynthesisGateError",
    "VALIDITY_FOOTER",
    "build_final_document",
    "can_synthesize",
    "validate_synthesis_gates",
]
