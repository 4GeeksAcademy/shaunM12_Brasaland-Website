"""Reporting HTTP API (Milestone 6 Phase 2)."""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from auth.dependencies import get_current_user
from celery_app import run_weekly_pipeline_task
from database import get_db
from users.models import UserResponse

from . import repository
from .schemas import (
    PipelineRunAccepted,
    PipelineRunOut,
    WeeklyLocationPerformanceOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["reporting"])


@router.get(
    "/weekly-location-performance",
    response_model=list[WeeklyLocationPerformanceOut],
)
def get_weekly_location_performance(
    week_start: date | None = Query(
        default=None,
        description="ISO week Monday (UTC). Defaults to latest computed week.",
    ),
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> list[WeeklyLocationPerformanceOut]:
    rows = repository.list_weekly_performance(session, week_start=week_start)
    return [WeeklyLocationPerformanceOut.model_validate(row) for row in rows]


@router.get("/pipeline-runs/latest", response_model=PipelineRunOut)
def get_latest_pipeline_run(
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> PipelineRunOut:
    run = repository.latest_pipeline_run(session)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pipeline runs recorded yet",
        )
    return PipelineRunOut.model_validate(run)


@router.post(
    "/pipeline-runs",
    response_model=PipelineRunAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_pipeline_run(
    _: UserResponse = Depends(get_current_user),
) -> PipelineRunAccepted:
    # Producer only: enqueue to Redis and return immediately (worker consumes).
    async_result = run_weekly_pipeline_task.delay(lookback_weeks=2)
    logger.info(
        "Enqueued weekly location performance pipeline task_id=%s",
        async_result.id,
    )
    return PipelineRunAccepted(task_id=async_result.id)
