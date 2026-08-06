"""Constants for Milestone 9 RFP workflow (context-27 Part 1)."""

from __future__ import annotations

from pathlib import Path

# --- Status machine (§4.3) ---------------------------------------------------

STATUS_ANALYZING = "analyzing"
STATUS_INTAKE_COMPLETE = "intake_complete"
STATUS_DISCARDED = "discarded"
STATUS_FAILED = "failed"
STATUS_DRAFTING = "drafting"
STATUS_UNDER_EVALUATION = "under_evaluation"
STATUS_WAITING_FOR_APPROVAL = "waiting_for_approval"
STATUS_AWAITING_DEPARTMENT_APPROVAL = "awaiting_department_approval"
STATUS_ARBITRATING = "arbitrating"
STATUS_AWAITING_CEO_APPROVAL = "awaiting_ceo_approval"
STATUS_COMPLETED = "completed"

P1_TERMINAL_STATUSES = frozenset(
    {STATUS_INTAKE_COMPLETE, STATUS_DISCARDED, STATUS_FAILED}
)

P3_TERMINAL_STATUSES = frozenset({STATUS_COMPLETED})

STATUS_VALUES = frozenset(
    {
        STATUS_ANALYZING,
        STATUS_INTAKE_COMPLETE,
        STATUS_DISCARDED,
        STATUS_FAILED,
        STATUS_DRAFTING,
        STATUS_UNDER_EVALUATION,
        STATUS_WAITING_FOR_APPROVAL,
        STATUS_AWAITING_DEPARTMENT_APPROVAL,
        STATUS_ARBITRATING,
        STATUS_AWAITING_CEO_APPROVAL,
        STATUS_COMPLETED,
    }
)

# --- Departments (§2.1) ------------------------------------------------------

DEPARTMENT_MARKETING = "marketing"
DEPARTMENT_OPERATIONS = "operations"
DEPARTMENT_PROCUREMENT = "procurement"
DEPARTMENT_TRAINING = "training"

DEPARTMENT_IDS = frozenset(
    {
        DEPARTMENT_MARKETING,
        DEPARTMENT_OPERATIONS,
        DEPARTMENT_PROCUREMENT,
        DEPARTMENT_TRAINING,
    }
)

# Owners per context-27 §2.1 — "who to approach" for each department.
DEPARTMENT_OWNERS: dict[str, str] = {
    DEPARTMENT_MARKETING: "Camila Ospina",
    DEPARTMENT_OPERATIONS: "Felipe Guerrero",
    DEPARTMENT_PROCUREMENT: "Lucia Fernandez",
    DEPARTMENT_TRAINING: "Jake Morrison",
}

DEPARTMENT_LABELS: dict[str, str] = {
    DEPARTMENT_MARKETING: "Marketing and Digital Experience",
    DEPARTMENT_OPERATIONS: "Restaurant Operations",
    DEPARTMENT_PROCUREMENT: "Procurement and Suppliers",
    DEPARTMENT_TRAINING: "Training and Quality Standards",
}

STATUS_LABELS: dict[str, str] = {
    STATUS_ANALYZING: "Analyzing",
    STATUS_INTAKE_COMPLETE: "Intake complete",
    STATUS_DISCARDED: "Discarded",
    STATUS_FAILED: "Failed",
    STATUS_DRAFTING: "Drafting",
    STATUS_UNDER_EVALUATION: "Under evaluation",
    STATUS_WAITING_FOR_APPROVAL: "Waiting for approval",
    STATUS_AWAITING_DEPARTMENT_APPROVAL: "Awaiting department approval",
    STATUS_ARBITRATING: "Arbitrating",
    STATUS_AWAITING_CEO_APPROVAL: "Awaiting CEO approval",
    STATUS_COMPLETED: "Done",
}

# --- Per-section approval status (Part 3 — M9-P3-15) -------------------------

APPROVAL_STATUS_AWAITING_HUMAN = "awaiting_human"
APPROVAL_STATUS_APPROVED = "approved"
APPROVAL_STATUS_REJECTED = "rejected"
APPROVAL_STATUS_CHANGES_REQUESTED = "changes_requested"

APPROVAL_STATUS_VALUES = frozenset(
    {
        APPROVAL_STATUS_AWAITING_HUMAN,
        APPROVAL_STATUS_APPROVED,
        APPROVAL_STATUS_REJECTED,
        APPROVAL_STATUS_CHANGES_REQUESTED,
    }
)

APPROVAL_STATUS_LABELS: dict[str, str] = {
    APPROVAL_STATUS_AWAITING_HUMAN: "Awaiting human approval",
    APPROVAL_STATUS_APPROVED: "Approved",
    APPROVAL_STATUS_REJECTED: "Rejected",
    APPROVAL_STATUS_CHANGES_REQUESTED: "Changes requested",
}

# Human decisions at dept interrupt (M9-P3-6)
APPROVAL_DECISION_APPROVE = "approve"
APPROVAL_DECISION_REJECT = "reject"
APPROVAL_DECISION_REQUEST_CHANGES = "request_changes"

APPROVAL_DECISION_VALUES = frozenset(
    {
        APPROVAL_DECISION_APPROVE,
        APPROVAL_DECISION_REJECT,
        APPROVAL_DECISION_REQUEST_CHANGES,
    }
)

# CEO gate decisions (M9-P3-11)
CEO_DECISION_APPROVE = "approve"
CEO_DECISION_REJECT = "reject"

CEO_DECISION_VALUES = frozenset({CEO_DECISION_APPROVE, CEO_DECISION_REJECT})

# --- Per-section draft status (Part 2 — §draft_status) ------------------------

DRAFT_STATUS_PENDING = "pending"
DRAFT_STATUS_DRAFTING = "drafting"
DRAFT_STATUS_EVALUATING = "evaluating"
DRAFT_STATUS_PASSED = "passed"
DRAFT_STATUS_NEEDS_HUMAN_REVIEW = "needs_human_review"

DRAFT_STATUS_VALUES = frozenset(
    {
        DRAFT_STATUS_PENDING,
        DRAFT_STATUS_DRAFTING,
        DRAFT_STATUS_EVALUATING,
        DRAFT_STATUS_PASSED,
        DRAFT_STATUS_NEEDS_HUMAN_REVIEW,
    }
)

DRAFT_STATUS_LABELS: dict[str, str] = {
    DRAFT_STATUS_PENDING: "Pending",
    DRAFT_STATUS_DRAFTING: "Drafting",
    DRAFT_STATUS_EVALUATING: "Evaluating",
    DRAFT_STATUS_PASSED: "Passed",
    DRAFT_STATUS_NEEDS_HUMAN_REVIEW: "Needs human review",
}

TERMINAL_DRAFT_STATUSES = frozenset(
    {DRAFT_STATUS_PASSED, DRAFT_STATUS_NEEDS_HUMAN_REVIEW}
)

# Minimum stored markdown length — shorter values trigger PDF re-conversion.
MIN_RFP_MARKDOWN_CHARS = 200


def department_owner(department_id: str) -> str:
    return DEPARTMENT_OWNERS.get(department_id, "Unassigned")


def department_label(department_id: str) -> str:
    if department_id in DEPARTMENT_LABELS:
        return DEPARTMENT_LABELS[department_id]
    return department_id.replace("_", " ").title()


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status.replace("_", " ").title())


def draft_status_label(draft_status: str | None) -> str:
    if not draft_status:
        return DRAFT_STATUS_LABELS[DRAFT_STATUS_PENDING]
    return DRAFT_STATUS_LABELS.get(
        draft_status,
        draft_status.replace("_", " ").title(),
    )


def approval_status_label(approval_status: str | None) -> str | None:
    if not approval_status:
        return None
    return APPROVAL_STATUS_LABELS.get(
        approval_status,
        approval_status.replace("_", " ").title(),
    )


# --- Compliance / business (§5, G4, H8) --------------------------------------

USD_COP_RATE = 4000
CEO_APPROVAL_THRESHOLD_USD = 50_000

COMPLIANCE_RULE_IDS = frozenset(
    {
        "COMPLIANCE_DUAL_CURRENCY",
        "COMPLIANCE_BRAND_PILLARS",
        "COMPLIANCE_MIN_LEAD_TIME_10_BD",
        "COMPLIANCE_NO_COMPETITORS",
        "COMPLIANCE_VALIDITY_30_DAYS",
        "COMPLIANCE_CEO_THRESHOLD_50K",
    }
)

# --- P2/P3 caps (cross-part locks in p1) ------------------------------------

MAX_GENERATOR_EVALUATOR_ITERATIONS = 3
MAX_ARBITRATION_ITERATIONS = 2

# --- Upload / processing -----------------------------------------------------

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_PDF_CONTENT_TYPES = frozenset({"application/pdf", "application/x-pdf"})

ERROR_PDF_CONVERSION_FAILED = "pdf_conversion_failed"
ERROR_LLM_UNAVAILABLE = "llm_unavailable"
ERROR_PIPELINE_ERROR = "pipeline_error"
ERROR_STORAGE_ERROR = "storage_error"

DISCARD_RULE_MISSING_CORE_FIELDS = "missing_core_fields"

# --- Paths -------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
RFP_SEED_ASSETS_DIR = (
    _REPO_ROOT / "memory-bank" / "historical-reference" / "assets" / "milestone-9"
)
# UI uploads land under data/raw/intakes/ (course rubric); checkpoints stay in data/rfp/.
RFP_INTAKE_PDF_DIR = _REPO_ROOT / "data" / "raw" / "intakes"
RFP_CHECKPOINT_DATA_DIR = _REPO_ROOT / "data" / "rfp"

SEED_PDF_FILES = (
    "CONTEXT-brasaland-request-1.pdf",
    "CONTEXT-brasaland-request-2.pdf",
    "CONTEXT-brasaland-request-3.pdf",
)

__all__ = [
    "ALLOWED_PDF_CONTENT_TYPES",
    "APPROVAL_DECISION_APPROVE",
    "APPROVAL_DECISION_REJECT",
    "APPROVAL_DECISION_REQUEST_CHANGES",
    "APPROVAL_DECISION_VALUES",
    "APPROVAL_STATUS_APPROVED",
    "APPROVAL_STATUS_AWAITING_HUMAN",
    "APPROVAL_STATUS_CHANGES_REQUESTED",
    "APPROVAL_STATUS_LABELS",
    "APPROVAL_STATUS_REJECTED",
    "APPROVAL_STATUS_VALUES",
    "CEO_APPROVAL_THRESHOLD_USD",
    "CEO_DECISION_APPROVE",
    "CEO_DECISION_REJECT",
    "CEO_DECISION_VALUES",
    "COMPLIANCE_RULE_IDS",
    "DEPARTMENT_IDS",
    "DEPARTMENT_LABELS",
    "DEPARTMENT_MARKETING",
    "DEPARTMENT_OPERATIONS",
    "DEPARTMENT_OWNERS",
    "DEPARTMENT_PROCUREMENT",
    "DEPARTMENT_TRAINING",
    "DISCARD_RULE_MISSING_CORE_FIELDS",
    "DRAFT_STATUS_DRAFTING",
    "DRAFT_STATUS_EVALUATING",
    "DRAFT_STATUS_LABELS",
    "DRAFT_STATUS_NEEDS_HUMAN_REVIEW",
    "DRAFT_STATUS_PASSED",
    "DRAFT_STATUS_PENDING",
    "DRAFT_STATUS_VALUES",
    "ERROR_LLM_UNAVAILABLE",
    "ERROR_PDF_CONVERSION_FAILED",
    "ERROR_PIPELINE_ERROR",
    "ERROR_STORAGE_ERROR",
    "MAX_ARBITRATION_ITERATIONS",
    "MAX_GENERATOR_EVALUATOR_ITERATIONS",
    "MIN_RFP_MARKDOWN_CHARS",
    "MAX_UPLOAD_BYTES",
    "P1_TERMINAL_STATUSES",
    "P3_TERMINAL_STATUSES",
    "RFP_INTAKE_PDF_DIR",
    "RFP_CHECKPOINT_DATA_DIR",
    "RFP_SEED_ASSETS_DIR",
    "SEED_PDF_FILES",
    "STATUS_ANALYZING",
    "STATUS_ARBITRATING",
    "STATUS_AWAITING_CEO_APPROVAL",
    "STATUS_AWAITING_DEPARTMENT_APPROVAL",
    "STATUS_COMPLETED",
    "STATUS_DISCARDED",
    "STATUS_DRAFTING",
    "STATUS_FAILED",
    "STATUS_INTAKE_COMPLETE",
    "STATUS_LABELS",
    "STATUS_UNDER_EVALUATION",
    "STATUS_VALUES",
    "STATUS_WAITING_FOR_APPROVAL",
    "TERMINAL_DRAFT_STATUSES",
    "approval_status_label",
    "department_label",
    "department_owner",
    "draft_status_label",
    "status_label",
    "USD_COP_RATE",
]
