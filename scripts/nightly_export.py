#!/usr/bin/env python3
"""DEV-53 nightly telemetry export + Milestone 6 pipeline trigger.

Independent of the FastAPI process. Lifecycle is recorded in reporting.job_runs.

Usage::

    python scripts/nightly_export.py
    TARGET_DATE=2026-07-14 python scripts/nightly_export.py

Pipeline subprocess (override with NIGHTLY_PIPELINE_CMD)::

    cd services/api && uv run python ../../data/pipelines/pipeline.py
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "services" / "api"

for _path in (str(API_ROOT), str(REPO_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from database import get_engine  # noqa: E402
from job_runner.export import export_telemetry_day_csv  # noqa: E402
from job_runner.models import (  # noqa: E402
    JOB_NAME_NIGHTLY_EXPORT,
    ensure_job_runs_schema,
)
from job_runner.repository import (  # noqa: E402
    ClaimOutcome,
    claim_nightly_job,
    complete_job,
    fail_job_if_processing,
)
from sqlmodel import Session  # noqa: E402
from telemetry.models import ensure_telemetry_schema  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("nightly_export")


def resolve_target_date() -> date:
    raw = os.environ.get("TARGET_DATE", "").strip()
    if raw:
        return date.fromisoformat(raw)
    return datetime.now(timezone.utc).date() - timedelta(days=1)


def resolve_raw_dir() -> Path:
    env = os.environ.get("NIGHTLY_RAW_DIR", "").strip()
    if env:
        return Path(env)
    env_root = os.environ.get("BRASALAND_REPO_ROOT", "").strip()
    if env_root:
        return Path(env_root) / "data" / "raw"
    return REPO_ROOT / "data" / "raw"


def resolve_pipeline_command() -> tuple[list[str], Path]:
    """Return ``(argv, cwd)`` for the Milestone 6 pipeline subprocess."""
    api_dir = API_ROOT if API_ROOT.is_dir() else Path("/app")

    override = os.environ.get("NIGHTLY_PIPELINE_CMD", "").strip()
    if override:
        return shlex.split(override), api_dir

    pipeline = REPO_ROOT / "data" / "pipelines" / "pipeline.py"
    env_root = os.environ.get("BRASALAND_REPO_ROOT", "").strip()
    if env_root:
        candidate = Path(env_root) / "data" / "pipelines" / "pipeline.py"
        if candidate.is_file():
            pipeline = candidate

    return ["uv", "run", "python", str(pipeline)], api_dir


def run_pipeline_subprocess() -> None:
    cmd, cwd = resolve_pipeline_command()

    env = os.environ.copy()
    repo = os.environ.get("BRASALAND_REPO_ROOT", str(REPO_ROOT))
    pythonpath_parts = [str(API_ROOT if API_ROOT.is_dir() else "/app"), str(repo)]
    existing = env.get("PYTHONPATH", "")
    if existing:
        pythonpath_parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    env.setdefault("BRASALAND_REPO_ROOT", str(repo))

    logger.info(
        "%s job_name=%s status=processing starting pipeline cmd=%s cwd=%s",
        datetime.now(timezone.utc).isoformat(),
        JOB_NAME_NIGHTLY_EXPORT,
        cmd,
        cwd,
    )
    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd.is_dir() else None,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Pipeline subprocess failed with exit code {completed.returncode}"
        )
    logger.info(
        "%s job_name=%s status=processing pipeline subprocess completed",
        datetime.now(timezone.utc).isoformat(),
        JOB_NAME_NIGHTLY_EXPORT,
    )


def run_nightly_export() -> int:
    """Run one nightly cycle. Returns process exit code."""
    target_date = resolve_target_date()
    logger.info(
        "%s job_name=%s status=pending start target_date=%s",
        datetime.now(timezone.utc).isoformat(),
        JOB_NAME_NIGHTLY_EXPORT,
        target_date,
    )

    engine = get_engine()
    job_id = None

    with Session(engine) as session:
        ensure_telemetry_schema(session)
        ensure_job_runs_schema(session)
        claim = claim_nightly_job(session, target_date=target_date)

        if claim.outcome == ClaimOutcome.SKIPPED_DUPLICATE:
            logger.info(
                "%s job_name=%s status=completed skipped duplicate target_date=%s",
                datetime.now(timezone.utc).isoformat(),
                JOB_NAME_NIGHTLY_EXPORT,
                target_date,
            )
            return 0

        if claim.outcome == ClaimOutcome.ABORTED_LOCKED:
            # Silent abort (exit 0) — another instance holds the lock.
            logger.info(
                "%s job_name=%s status=processing aborted silent lock target_date=%s",
                datetime.now(timezone.utc).isoformat(),
                JOB_NAME_NIGHTLY_EXPORT,
                target_date,
            )
            return 0

    assert claim.job is not None and claim.job.id is not None
    job_id = claim.job.id

    succeeded = False
    exit_code = 1
    error_message = "nightly export aborted without completion"
    try:
        with Session(engine) as session:
            export_telemetry_day_csv(
                session,
                target_date=target_date,
                raw_dir=resolve_raw_dir(),
            )

        run_pipeline_subprocess()

        with Session(engine) as session:
            complete_job(session, job_id)

        succeeded = True
        exit_code = 0
        logger.info(
            "%s job_name=%s status=completed finished target_date=%s",
            datetime.now(timezone.utc).isoformat(),
            JOB_NAME_NIGHTLY_EXPORT,
            target_date,
        )
    except Exception as exc:
        error_message = str(exc)
        logger.exception(
            "%s job_name=%s status=failed target_date=%s error=%s",
            datetime.now(timezone.utc).isoformat(),
            JOB_NAME_NIGHTLY_EXPORT,
            target_date,
            exc,
        )
        exit_code = 1
    finally:
        # Guarantee no zombie ``processing`` row after handled failure / early exit.
        # No-op when already ``completed`` (succeeded) or already ``failed``.
        if job_id is not None and not succeeded:
            try:
                with Session(engine) as session:
                    fail_job_if_processing(session, job_id, error_message)
            except Exception:
                logger.exception(
                    "%s job_name=%s status=failed could not persist failure row",
                    datetime.now(timezone.utc).isoformat(),
                    JOB_NAME_NIGHTLY_EXPORT,
                )

    return exit_code


def main() -> int:
    return run_nightly_export()


if __name__ == "__main__":
    raise SystemExit(main())
