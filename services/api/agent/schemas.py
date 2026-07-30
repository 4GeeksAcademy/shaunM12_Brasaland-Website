"""Request/response schemas for the Support Agent endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural-language question")


class AgentQueryResponse(BaseModel):
    """Client-facing answer only — trace stays server-side (context-23 P1-L6)."""

    answer: str
