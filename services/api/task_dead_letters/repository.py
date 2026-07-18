"""Persist exhausted Celery failures to ``task_dead_letters``."""

from __future__ import annotations

import logging

from sqlmodel import Session, select

from database import get_engine

from .models import TaskDeadLetter

logger = logging.getLogger(__name__)


def record_dead_letter(
    *,
    task_id: str,
    attempt: int,
    error_message: str,
    task_name: str | None = None,
) -> None:
    """Insert or update one DLQ row per ``task_id`` (exhausted retries only)."""
    engine = get_engine()
    with Session(engine) as session:
        existing = session.exec(
            select(TaskDeadLetter).where(TaskDeadLetter.task_id == task_id)
        ).first()
        if existing is not None:
            existing.attempt = attempt
            existing.error_message = error_message
            existing.task_name = task_name
            session.add(existing)
        else:
            session.add(
                TaskDeadLetter(
                    task_id=task_id,
                    attempt=attempt,
                    error_message=error_message,
                    task_name=task_name,
                )
            )
        session.commit()
    logger.error(
        "Recorded dead letter task_id=%s attempt=%s task_name=%s error=%s",
        task_id,
        attempt,
        task_name,
        error_message,
    )
