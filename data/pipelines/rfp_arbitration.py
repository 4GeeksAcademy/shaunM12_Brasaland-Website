"""P3 arbitration — deterministic cross-department conflict resolution (context-27 P3 M9-P3-12)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from data.pipelines.rfp_intake import _ensure_repo_root_on_path

_ensure_repo_root_on_path()

from rfp.constants import (  # noqa: E402
    DEPARTMENT_MARKETING,
    MAX_ARBITRATION_ITERATIONS,
)

RULE_COMPLIANCE_STRICTEST = "ARBITRATION_COMPLIANCE_STRICTEST"
RULE_STRICTEST_OPERATIONAL = "ARBITRATION_STRICTEST_OPERATIONAL"
RULE_MARKETING_PREFERENCE = "ARBITRATION_MARKETING_PREFERENCE"
RULE_UNRESOLVED = "ARBITRATION_UNRESOLVED"

MARKETING_PREFERENCE_FIELDS = frozenset(
    {
        "validity",
        "validity_days",
        "brand",
        "exclusivity",
        "co_branding",
    }
)

OPERATIONAL_STRICTEST_FIELDS = frozenset(
    {
        "lead_time_business_days",
        "setup_lead_time_business_days",
        "delivery_lead_time_business_days",
    }
)

_LEAD_TIME_PATTERN = re.compile(r"(\d+)\s*(?:business\s+)?days?", re.IGNORECASE)
_LEAD_TIME_CONTEXT = (
    "setup",
    "delivery",
    "install",
    "deploy",
    "implementation",
    "lead time",
    "lead-time",
    "go-live",
    "rollout",
)
_VALIDITY_PATTERN = re.compile(
    r"(?:valid(?:ity)?|offer)\s*(?:for|of)?\s*(\d+)\s*days?",
    re.IGNORECASE,
)
_ISO_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass
class ArbitrationResult:
    resolutions: list[dict[str, Any]] = field(default_factory=list)
    remaining_conflicts: list[dict[str, Any]] = field(default_factory=list)
    arbitration_exhausted: bool = False
    rounds_used: int = 0


def _normalize_claims(raw: dict[str, Any]) -> list[dict[str, str]]:
    claims = raw.get("claims") or []
    normalized: list[dict[str, str]] = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        dept = str(claim.get("department_id") or "").strip()
        value = str(claim.get("value") or "").strip()
        if dept and value:
            normalized.append({"department_id": dept, "value": value})
    return normalized


def merge_conflict_lists(
    intake_conflicts: list[dict[str, Any]] | None,
    detected_conflicts: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for source in (intake_conflicts or []) + (detected_conflicts or []):
        if not isinstance(source, dict):
            continue
        field_name = str(source.get("field") or "").strip()
        if not field_name:
            continue
        claims = _normalize_claims(source)
        if len(claims) < 2:
            continue
        if field_name in merged:
            existing = {c["department_id"]: c["value"] for c in _normalize_claims(merged[field_name])}
            for claim in claims:
                existing[claim["department_id"]] = claim["value"]
            merged[field_name]["claims"] = [
                {"department_id": d, "value": v} for d, v in sorted(existing.items())
            ]
        else:
            merged[field_name] = {"field": field_name, "claims": claims}
    return list(merged.values())


def _extract_lead_time_claims(approved_drafts: dict[str, str]) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    for dept, draft in approved_drafts.items():
        for match in _LEAD_TIME_PATTERN.finditer(draft or ""):
            context = draft[max(0, match.start() - 40) : match.end() + 40].lower()
            if not any(token in context for token in _LEAD_TIME_CONTEXT):
                continue
            days = int(match.group(1))
            claims.append({"department_id": dept, "value": str(days)})
            break
    return claims


def _extract_validity_claims(approved_drafts: dict[str, str]) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    for dept, draft in approved_drafts.items():
        match = _VALIDITY_PATTERN.search(draft or "")
        if match:
            claims.append({"department_id": dept, "value": match.group(1)})
    return claims


def detect_draft_conflicts(approved_drafts: dict[str, str]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    lead_claims = _extract_lead_time_claims(approved_drafts)
    if len(lead_claims) >= 2 and len({c["value"] for c in lead_claims}) > 1:
        conflicts.append({"field": "lead_time_business_days", "claims": lead_claims})
    validity_claims = _extract_validity_claims(approved_drafts)
    if len(validity_claims) >= 2 and len({c["value"] for c in validity_claims}) > 1:
        conflicts.append({"field": "validity_days", "claims": validity_claims})
    return conflicts


def collect_conflicts(
    *,
    intake_conflicts: list[dict[str, Any]] | None,
    approved_drafts: dict[str, str],
) -> list[dict[str, Any]]:
    return merge_conflict_lists(intake_conflicts, detect_draft_conflicts(approved_drafts))


def _parse_numeric(value: str) -> float | None:
    try:
        return float(value.strip().replace(",", ""))
    except ValueError:
        return None


def _parse_date(value: str) -> datetime | None:
    match = _ISO_DATE.search(value)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d")
    except ValueError:
        return None


def _pick_strictest_operational(claims: list[dict[str, str]], field_name: str) -> dict[str, Any] | None:
    best: dict[str, str] | None = None
    best_score: float | None = None
    for claim in claims:
        value = claim["value"]
        parsed_date = _parse_date(value)
        score = parsed_date.timestamp() if parsed_date else _parse_numeric(value)
        if score is None:
            return None
        if best_score is None or score > best_score:
            best_score = score
            best = claim
    if best is None:
        return None
    return {
        "field": field_name,
        "winning_department_id": best["department_id"],
        "resolved_value": best["value"],
        "rule_id": RULE_STRICTEST_OPERATIONAL,
    }


def _pick_marketing(claims: list[dict[str, str]], field_name: str) -> dict[str, Any] | None:
    for claim in claims:
        if claim["department_id"] == DEPARTMENT_MARKETING:
            return {
                "field": field_name,
                "winning_department_id": DEPARTMENT_MARKETING,
                "resolved_value": claim["value"],
                "rule_id": RULE_MARKETING_PREFERENCE,
            }
    return None


def arbitrate_conflict(conflict: dict[str, Any], *, iteration: int) -> dict[str, Any]:
    field_name = str(conflict.get("field") or "")
    claims = _normalize_claims(conflict)
    if len(claims) < 2:
        return {
            "field": field_name,
            "rule_id": RULE_UNRESOLVED,
            "iteration": iteration,
            "unresolved": True,
            "claims": claims,
        }

    if len({c["value"] for c in claims}) == 1:
        winner = claims[0]
        return {
            "field": field_name,
            "winning_department_id": winner["department_id"],
            "resolved_value": winner["value"],
            "rule_id": RULE_COMPLIANCE_STRICTEST,
            "iteration": iteration,
        }

    if field_name in MARKETING_PREFERENCE_FIELDS:
        marketing = _pick_marketing(claims, field_name)
        if marketing is not None:
            marketing["iteration"] = iteration
            return marketing

    if field_name in OPERATIONAL_STRICTEST_FIELDS or field_name == "deadline":
        operational = _pick_strictest_operational(claims, field_name)
        if operational is not None:
            operational["iteration"] = iteration
            return operational

    if field_name == "lead_time_business_days":
        numeric_claims = [(c, _parse_numeric(c["value"])) for c in claims]
        if all(n is not None for _, n in numeric_claims):
            winner = max(numeric_claims, key=lambda pair: pair[1] or 0)[0]
            return {
                "field": field_name,
                "winning_department_id": winner["department_id"],
                "resolved_value": winner["value"],
                "rule_id": RULE_COMPLIANCE_STRICTEST,
                "iteration": iteration,
            }

    return {
        "field": field_name,
        "rule_id": RULE_UNRESOLVED,
        "iteration": iteration,
        "unresolved": True,
        "claims": claims,
    }


def run_arbitration(
    conflicts: list[dict[str, Any]],
    *,
    max_iterations: int | None = None,
) -> ArbitrationResult:
    cap = max_iterations if max_iterations is not None else MAX_ARBITRATION_ITERATIONS
    pending = list(conflicts)
    resolutions: list[dict[str, Any]] = []
    rounds_used = 0

    for round_num in range(1, cap + 1):
        if not pending:
            break
        rounds_used = round_num
        still_pending: list[dict[str, Any]] = []
        for conflict in pending:
            outcome = arbitrate_conflict(conflict, iteration=round_num)
            if outcome.get("unresolved"):
                still_pending.append(conflict)
            else:
                resolutions.append(outcome)
        pending = still_pending

    exhausted = bool(pending) and rounds_used >= cap
    return ArbitrationResult(
        resolutions=resolutions,
        remaining_conflicts=pending,
        arbitration_exhausted=exhausted,
        rounds_used=rounds_used,
    )


__all__ = [
    "ArbitrationResult",
    "RULE_COMPLIANCE_STRICTEST",
    "RULE_MARKETING_PREFERENCE",
    "RULE_STRICTEST_OPERATIONAL",
    "RULE_UNRESOLVED",
    "arbitrate_conflict",
    "collect_conflicts",
    "detect_draft_conflicts",
    "merge_conflict_lists",
    "run_arbitration",
]
