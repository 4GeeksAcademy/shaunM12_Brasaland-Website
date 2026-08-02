"""Request/response schemas for the Support Agent endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural-language question")


class AgentQueryResponse(BaseModel):
    """Client-facing answer only — trace stays server-side (context-23 P1-L6)."""

    answer: str


class GuardrailSummaryResponse(BaseModel):
    """In-process guardrail counters since API start (context-25 P25-L22b)."""

    since: str
    blocks: int
    redirects: int
    validation_failures: int
    by_failure_type: dict[str, int] = Field(default_factory=dict)
    by_reason: dict[str, int] = Field(default_factory=dict)
