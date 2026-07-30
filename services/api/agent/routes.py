"""Support Agent HTTP routes (context-23 Part 1 Phase 2).

Thin handlers — orchestration lives in ``agent.graph``; RAG primitives in
``data.pipelines.rag``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from auth.dependencies import get_current_user
from knowledge.bootstrap import ensure_repo_root_on_path
from users.models import UserResponse

from .graph import invoke_support_agent
from .schemas import AgentQueryRequest, AgentQueryResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agent"])


@router.post("/query", response_model=AgentQueryResponse)
def agent_query(
    body: AgentQueryRequest,
    _: UserResponse = Depends(get_current_user),
) -> AgentQueryResponse:
    """Run the compiled LangGraph and return the final answer string only."""
    question = body.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="question must not be empty",
        )

    try:
        ensure_repo_root_on_path()
        state = invoke_support_agent(question)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception:
        logger.exception("support agent query failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Support Agent failed to answer. Try again shortly.",
        ) from None

    logger.info(
        "support agent query route=%s trace=%s",
        state.get("route"),
        state.get("trace_events"),
    )
    return AgentQueryResponse(answer=state["answer"])
