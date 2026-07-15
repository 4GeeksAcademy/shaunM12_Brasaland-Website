"""Create / claim / finalize ``reporting.job_runs`` rows."""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from .models import (
    JOB_NAME_NIGHTLY_EXPORT,
    STALE_PROCESSING_HOURS_DEFAULT,
    JobRun,
    JobRunStatus,
    ensure_job_runs_schema,
)

logger = logging.getLogger("job_runner")


class ClaimOutcome(str, Enum):
    CLAIMED = "claimed"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    ABORTED_LOCKED = "aborted_locked"


@dataclass
class ClaimResult:
    outcome: ClaimOutcome
    job: Optional[JobRun] = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stale_hours() -> float:
    raw = os.environ.get("JOB_PROCESSING_STALE_HOURS", "").strip()
    if not raw:
        return float(STALE_PROCESSING_HOURS_DEFAULT)
    return float(raw)


def _log(job_name: str, status: str, message: str, *, level: int = logging.INFO) -> None:
    logger.log(
        level,
        "%s job_name=%s status=%s %s",
        _utc_now().isoformat(),
        job_name,
        status,
        message,
    )


def has_processing_lock(session: Session, job_name: str) -> bool:
    """True when a non-stale ``processing`` row exists for ``job_name``."""
    ensure_job_runs_schema(session)
    recover_stale_processing(session, job_name)
    row = session.exec(
        select(JobRun).where(
            JobRun.job_name == job_name,
            JobRun.status == JobRunStatus.PROCESSING.value,
        )
    ).first()
    return row is not None


def has_completed_for_date(
    session: Session, job_name: str, target_date: date
) -> bool:
    ensure_job_runs_schema(session)
    row = session.exec(
        select(JobRun).where(
            JobRun.job_name == job_name,
            JobRun.target_date == target_date,
            JobRun.status == JobRunStatus.COMPLETED.value,
        )
    ).first()
    return row is not None


def recover_stale_processing(session: Session, job_name: str) -> int:
    """Mark stale ``processing`` rows as ``failed``. Returns count recovered."""
    ensure_job_runs_schema(session)
    cutoff = _utc_now() - timedelta(hours=_stale_hours())
    rows = session.exec(
        select(JobRun).where(
            JobRun.job_name == job_name,
            JobRun.status == JobRunStatus.PROCESSING.value,
        )
    ).all()
    recovered = 0
    for row in rows:
        started = row.started_at or row.created_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if started <= cutoff:
            row.status = JobRunStatus.FAILED.value
            row.finished_at = _utc_now()
            row.error_message = (
                f"Stale processing lock recovered "
                f"(older than {_stale_hours():g}h)"
            )
            session.add(row)
            recovered += 1
            _log(
                job_name,
                JobRunStatus.FAILED.value,
                f"stale lock recovered job_id={row.id} target_date={row.target_date}",
                level=logging.ERROR,
            )
    if recovered:
        session.commit()
    return recovered


def claim_nightly_job(
    session: Session,
    *,
    target_date: date,
    job_name: str = JOB_NAME_NIGHTLY_EXPORT,
) -> ClaimResult:
    """Create/claim a job row: pending → processing, or skip/abort."""
    ensure_job_runs_schema(session)
    recover_stale_processing(session, job_name)

    if has_completed_for_date(session, job_name, target_date):
        _log(
            job_name,
            JobRunStatus.COMPLETED.value,
            f"skipped duplicate target_date={target_date}",
        )
        return ClaimResult(outcome=ClaimOutcome.SKIPPED_DUPLICATE)

    if has_processing_lock(session, job_name):
        _log(
            job_name,
            JobRunStatus.PROCESSING.value,
            f"aborted: processing lock held target_date={target_date}",
        )
        return ClaimResult(outcome=ClaimOutcome.ABORTED_LOCKED)

    row = session.exec(
        select(JobRun).where(
            JobRun.job_name == job_name,
            JobRun.target_date == target_date,
        )
    ).first()

    now = _utc_now()
    if row is None:
        row = JobRun(
            job_name=job_name,
            target_date=target_date,
            status=JobRunStatus.PENDING.value,
            created_at=now,
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            row = session.exec(
                select(JobRun).where(
                    JobRun.job_name == job_name,
                    JobRun.target_date == target_date,
                )
            ).first()
            if row is None:
                raise
            if row.status == JobRunStatus.COMPLETED.value:
                _log(
                    job_name,
                    JobRunStatus.COMPLETED.value,
                    f"skipped duplicate target_date={target_date}",
                )
                return ClaimResult(outcome=ClaimOutcome.SKIPPED_DUPLICATE)
            if row.status == JobRunStatus.PROCESSING.value:
                _log(
                    job_name,
                    JobRunStatus.PROCESSING.value,
                    f"aborted: processing lock held target_date={target_date}",
                )
                return ClaimResult(outcome=ClaimOutcome.ABORTED_LOCKED)
        else:
            session.refresh(row)
            _log(
                job_name,
                JobRunStatus.PENDING.value,
                f"created target_date={target_date}",
            )

    if row.status == JobRunStatus.COMPLETED.value:
        _log(
            job_name,
            JobRunStatus.COMPLETED.value,
            f"skipped duplicate target_date={target_date}",
        )
        return ClaimResult(outcome=ClaimOutcome.SKIPPED_DUPLICATE)

    # Re-check lock after insert race windows.
    recover_stale_processing(session, job_name)
    other = session.exec(
        select(JobRun).where(
            JobRun.job_name == job_name,
            JobRun.status == JobRunStatus.PROCESSING.value,
            JobRun.id != row.id,
        )
    ).first()
    if other is not None:
        _log(
            job_name,
            JobRunStatus.PROCESSING.value,
            f"aborted: processing lock held by job_id={other.id}",
        )
        return ClaimResult(outcome=ClaimOutcome.ABORTED_LOCKED)

    row.status = JobRunStatus.PROCESSING.value
    row.started_at = now
    row.finished_at = None
    row.error_message = None
    session.add(row)
    session.commit()
    session.refresh(row)

    # Enforce single-flight: at most one processing row for this job_name.
    rivals = session.exec(
        select(JobRun).where(
            JobRun.job_name == job_name,
            JobRun.status == JobRunStatus.PROCESSING.value,
            JobRun.id != row.id,
        )
    ).all()
    if rivals:
        row.status = JobRunStatus.PENDING.value
        row.started_at = None
        session.add(row)
        session.commit()
        _log(
            job_name,
            JobRunStatus.PROCESSING.value,
            f"aborted: lost single-flight race to job_id={rivals[0].id}",
        )
        return ClaimResult(outcome=ClaimOutcome.ABORTED_LOCKED)

    _log(
        job_name,
        JobRunStatus.PROCESSING.value,
        f"claimed job_id={row.id} target_date={target_date}",
    )
    return ClaimResult(outcome=ClaimOutcome.CLAIMED, job=row)


def complete_job(session: Session, job_id: uuid.UUID) -> JobRun:
    ensure_job_runs_schema(session)
    row = session.get(JobRun, job_id)
    if row is None:
        raise LookupError(f"job_runs row not found: {job_id}")
    row.status = JobRunStatus.COMPLETED.value
    row.finished_at = _utc_now()
    row.error_message = None
    session.add(row)
    session.commit()
    session.refresh(row)
    _log(
        row.job_name,
        JobRunStatus.COMPLETED.value,
        f"finished job_id={row.id} target_date={row.target_date}",
    )
    return row


def fail_job(
    session: Session, job_id: uuid.UUID, error_message: str
) -> JobRun:
    ensure_job_runs_schema(session)
    row = session.get(JobRun, job_id)
    if row is None:
        raise LookupError(f"job_runs row not found: {job_id}")
    row.status = JobRunStatus.FAILED.value
    row.finished_at = _utc_now()
    row.error_message = (error_message or "unknown error")[:4000]
    session.add(row)
    session.commit()
    session.refresh(row)
    _log(
        row.job_name,
        JobRunStatus.FAILED.value,
        f"failed job_id={row.id} target_date={row.target_date} error={row.error_message}",
        level=logging.ERROR,
    )
    return row


def fail_job_if_processing(
    session: Session, job_id: uuid.UUID, error_message: str
) -> Optional[JobRun]:
    """Mark ``failed`` only when the row is still ``processing``.

    Safe for ``finally`` blocks: no-op if already ``completed`` or ``failed``.
    """
    ensure_job_runs_schema(session)
    row = session.get(JobRun, job_id)
    if row is None:
        return None
    if row.status != JobRunStatus.PROCESSING.value:
        return row
    return fail_job(session, job_id, error_message)
