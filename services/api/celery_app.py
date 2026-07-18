"""Celery application and async tasks (DEV-55).

Broker and result backend both use ``REDIS_URL``. Workers must run as a
separate process: ``uv run celery -A celery_app worker --loglevel=info``.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from celery import Celery, Task
from celery.exceptions import SoftTimeLimitExceeded

import config

logger = logging.getLogger(__name__)

celery_app = Celery(
    "brasaland",
    broker=config.REDIS_URL,
    backend=config.REDIS_URL,
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Prefer late ack so a crashed worker requeues the message.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


class DeadLetterTask(Task):
    """Base task that records exhausted failures in ``task_dead_letters``."""

    abstract = True

    def on_failure(
        self,
        exc: BaseException,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        # Called after retries are exhausted (permanent failure).
        attempt = int(self.request.retries) + 1
        try:
            from task_dead_letters import record_dead_letter

            record_dead_letter(
                task_id=task_id,
                attempt=attempt,
                error_message=str(exc),
                task_name=self.name,
            )
        except Exception:
            logger.exception(
                "Failed to persist dead letter task_id=%s",
                task_id,
            )


def _log_task_outcome(
    *,
    task_id: str,
    attempt: int,
    status: str,
    duration_s: float,
    error: str | None = None,
) -> None:
    if error:
        logger.error(
            "task_id=%s attempt=%s status=%s duration_s=%.3f error=%s",
            task_id,
            attempt,
            status,
            duration_s,
            error,
        )
    else:
        logger.info(
            "task_id=%s attempt=%s status=%s duration_s=%.3f",
            task_id,
            attempt,
            status,
            duration_s,
        )


@celery_app.task(
    bind=True,
    base=DeadLetterTask,
    name="celery_app.run_weekly_pipeline_task",
    max_retries=2,
    soft_time_limit=600,
    time_limit=720,
)
def run_weekly_pipeline_task(self: Task, lookback_weeks: int = 2) -> dict[str, Any]:
    """Enqueueable wrapper around the weekly location performance pipeline."""
    task_id = self.request.id or "unknown"
    attempt = int(self.request.retries) + 1
    started = time.perf_counter()
    try:
        from reporting.runner import run_weekly_pipeline

        run_weekly_pipeline(lookback_weeks=lookback_weeks)
        duration_s = time.perf_counter() - started
        _log_task_outcome(
            task_id=task_id,
            attempt=attempt,
            status="success",
            duration_s=duration_s,
        )
        return {"status": "completed", "lookback_weeks": lookback_weeks}
    except SoftTimeLimitExceeded as exc:
        duration_s = time.perf_counter() - started
        _log_task_outcome(
            task_id=task_id,
            attempt=attempt,
            status="failure",
            duration_s=duration_s,
            error=str(exc),
        )
        raise
    except Exception as exc:
        duration_s = time.perf_counter() - started
        _log_task_outcome(
            task_id=task_id,
            attempt=attempt,
            status="failure",
            duration_s=duration_s,
            error=str(exc),
        )
        # Exponential backoff: 2, 4 seconds for retries 1 and 2 (never immediate).
        countdown = 2 ** attempt
        raise self.retry(exc=exc, countdown=countdown) from exc


@celery_app.task(
    bind=True,
    base=DeadLetterTask,
    name="celery_app.force_failure_task",
    max_retries=2,
)
def force_failure_task(self: Task, reason: str = "forced demo failure") -> None:
    """Demo/eval helper: always fails (with backoff) then lands in the DLQ."""
    task_id = self.request.id or "unknown"
    attempt = int(self.request.retries) + 1
    started = time.perf_counter()
    error = reason
    duration_s = time.perf_counter() - started
    _log_task_outcome(
        task_id=task_id,
        attempt=attempt,
        status="failure",
        duration_s=duration_s,
        error=error,
    )
    countdown = 2 ** attempt
    raise self.retry(exc=RuntimeError(error), countdown=countdown)
