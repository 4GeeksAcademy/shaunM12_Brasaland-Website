"""Pydantic request/response schemas for RFP endpoints (Part 1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RfpSectionResponse(BaseModel):
    department_id: str
    department_label: str
    department_owner: str
    key_aspects: list[str] = Field(default_factory=list)
    draft_status: str
    draft_status_label: str
    draft_content: str | None = None
    evaluation_results: dict[str, Any] | None = None
    approval_status: str | None = None
    approval_status_label: str | None = None
    approver: str | None = None
    approved_at: datetime | None = None
    approval_comment: str | None = None


class RfpCeoApprovalPacketResponse(BaseModel):
    client_name: str | None = None
    estimated_contract_value_usd: float | None = None
    threshold_reason: str | None = None
    requires_ceo_approval: bool = False
    approved_excerpts: dict[str, str] = Field(default_factory=dict)
    arbitration_resolutions: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)


class RfpTraceEventResponse(BaseModel):
    id: int
    node: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RfpTicketSummaryResponse(BaseModel):
    ticket_id: str
    status: str
    status_label: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    departments_needed: list[str] = Field(default_factory=list)
    requires_ceo_approval: bool = False
    created_at: datetime
    updated_at: datetime


class RfpTicketDetailResponse(RfpTicketSummaryResponse):
    unmapped_topics: list[str] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    intake_summary: str | None = None
    discard_reason: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    markdown_length: int = 0
    has_markdown: bool = False
    has_final_document: bool = False
    final_document_length: int = 0
    arbitration_exhausted: bool = False
    arbitration_resolutions: list[dict[str, Any]] = Field(default_factory=list)
    ceo_approval_comment: str | None = None
    ceo_approval_packet: RfpCeoApprovalPacketResponse | None = None
    sections: list[RfpSectionResponse] = Field(default_factory=list)


class RfpTicketCreateResponse(BaseModel):
    ticket_id: str
    status: str
    created_at: datetime


class RfpDraftStartResponse(BaseModel):
    ticket_id: str
    status: str
    status_label: str


class RfpDepartmentDecisionRequest(BaseModel):
    decision: str
    comment: str | None = None


class RfpDepartmentDecisionResponse(BaseModel):
    ticket_id: str
    department_id: str
    decision: str
    status: str
    status_label: str
    approval_status: str | None = None
    approval_status_label: str | None = None


class RfpRegenerateResponse(BaseModel):
    ticket_id: str
    department_id: str
    status: str
    status_label: str
    draft_status: str
    draft_status_label: str
    approval_status: str | None = None
    approval_status_label: str | None = None


class RfpCeoDecisionRequest(BaseModel):
    decision: str
    comment: str | None = None


class RfpCeoDecisionResponse(BaseModel):
    ticket_id: str
    decision: str
    status: str
    status_label: str


class RfpApprovalStartResponse(BaseModel):
    ticket_id: str
    status: str
    status_label: str


class RfpFinalDocumentResponse(BaseModel):
    ticket_id: str
    final_document_markdown: str
    generated_at: datetime


__all__ = [
    "RfpApprovalStartResponse",
    "RfpCeoApprovalPacketResponse",
    "RfpCeoDecisionRequest",
    "RfpCeoDecisionResponse",
    "RfpDepartmentDecisionRequest",
    "RfpDepartmentDecisionResponse",
    "RfpDraftStartResponse",
    "RfpFinalDocumentResponse",
    "RfpRegenerateResponse",
    "RfpSectionResponse",
    "RfpTicketCreateResponse",
    "RfpTicketDetailResponse",
    "RfpTicketSummaryResponse",
    "RfpTraceEventResponse",
]
