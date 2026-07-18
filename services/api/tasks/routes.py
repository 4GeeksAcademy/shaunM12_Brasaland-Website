"""Celery task status HTTP API (DEV-55)."""

from __future__ import annotations

from typing import Any, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth.dependencies import get_current_user
from celery_app import celery_app
from users.models import UserResponse

router = APIRouter(tags=["tasks"])

_STATUS_MAP = {
    "PENDING": "pending",
    "STARTED": "started",
    "SUCCESS": "success",
    "FAILURE": "failure",
    "RETRY": "pending",
    "REVOKED": "failure",
}


class TaskStatusOut(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None


def map_celery_state(state: str) -> str:
    return _STATUS_MAP.get(state.upper(), "pending")


@router.get("/{task_id}", response_model=TaskStatusOut)
def get_task_status(
    task_id: str,
    _: UserResponse = Depends(get_current_user),
) -> TaskStatusOut:
    """Return Celery task lifecycle status (unknown ids appear as pending)."""
    async_result = AsyncResult(task_id, app=celery_app)
    state = async_result.state or "PENDING"
    status = map_celery_state(state)

    result: Any = None
    if state == "SUCCESS":
        result = async_result.result
    elif state == "FAILURE":
        result = {"error": str(async_result.result)}

    return TaskStatusOut(task_id=task_id, status=status, result=result)
