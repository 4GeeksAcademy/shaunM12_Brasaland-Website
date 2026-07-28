"""Request/response schemas for the knowledge RAG endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class KnowledgeQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural-language question")


class KnowledgeQueryResponse(BaseModel):
    """Client-facing answer only — never chunks, scores, or Qdrant payloads."""

    answer: str


class KnowledgeReindexResponse(BaseModel):
    status: str = "ok"
    chunks_indexed: int
