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
    draft_content: str | None = None
    evaluation_results: dict[str, Any] | None = None
    approval_status: str | None = None


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
    sections: list[RfpSectionResponse] = Field(default_factory=list)


class RfpTicketCreateResponse(BaseModel):
    ticket_id: str
    status: str
    created_at: datetime


__all__ = [
    "RfpSectionResponse",
    "RfpTicketCreateResponse",
    "RfpTicketDetailResponse",
    "RfpTicketSummaryResponse",
]
