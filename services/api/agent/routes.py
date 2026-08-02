"""Support Agent HTTP routes (context-23 Part 1 Phase 2).

Thin handlers — orchestration lives in ``agent.graph``; RAG primitives in
``data.pipelines.rag``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from auth.dependencies import get_current_user
from knowledge.bootstrap import ensure_repo_root_on_path
from users.models import UserResponse

from .graph import invoke_support_agent
from .guardrails.summary import build_guardrail_summary_response
from .schemas import AgentQueryRequest, AgentQueryResponse, GuardrailSummaryResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agent"])


@router.post("/query", response_model=AgentQueryResponse)
def agent_query(
    body: AgentQueryRequest,
    request: Request,
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
        auth_header = request.headers.get("Authorization")
        state = invoke_support_agent(question, auth_header=auth_header)
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


@router.get("/guardrails/summary", response_model=GuardrailSummaryResponse)
def agent_guardrails_summary(
    _: UserResponse = Depends(get_current_user),
) -> GuardrailSummaryResponse:
    """Return in-memory guardrail counters for the running API process."""
    return build_guardrail_summary_response()
