"""Knowledge RAG HTTP routes (context-21 Phase 3).

Thin handlers — retrieval/generation live in ``data.pipelines.rag``;
indexing lives in ``data.process.rag``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from auth.dependencies import get_current_user
from users.models import UserResponse

from .bootstrap import ensure_repo_root_on_path
from .schemas import (
    KnowledgeQueryRequest,
    KnowledgeQueryResponse,
    KnowledgeReindexResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["knowledge"])


@router.post("/query", response_model=KnowledgeQueryResponse)
def knowledge_query(
    body: KnowledgeQueryRequest,
    _: UserResponse = Depends(get_current_user),
) -> KnowledgeQueryResponse:
    """Answer from retrieved context via the generation model — answer string only."""
    question = body.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="question must not be empty",
        )

    try:
        ensure_repo_root_on_path()
        from data.pipelines.rag import query as rag_query

        answer = rag_query(question)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception:
        logger.exception("knowledge query failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Knowledge assistant failed to answer. Try again shortly.",
        ) from None

    return KnowledgeQueryResponse(answer=answer)


@router.post("/reindex", response_model=KnowledgeReindexResponse)
def knowledge_reindex(
    _: UserResponse = Depends(get_current_user),
) -> KnowledgeReindexResponse:
    """Re-run ``setup()`` upsert for any authenticated user (L12).

    Does not wipe/recreate the collection — that remains CLI-only.
    """
    try:
        ensure_repo_root_on_path()
        from data.process.rag import setup as rag_setup

        chunks_indexed = rag_setup(dry_run=False)
    except Exception:
        logger.exception("knowledge reindex failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Knowledge reindex failed. Check Qdrant and embedding config.",
        ) from None

    return KnowledgeReindexResponse(status="ok", chunks_indexed=chunks_indexed)
