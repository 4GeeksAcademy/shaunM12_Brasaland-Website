"""Background runner that invokes the Prefect weekly pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _ensure_repo_root_on_path() -> Path:
    """Prefer repo-root ``data`` package over ``services/api/data`` TinyDB dir."""
    api_dir = Path(__file__).resolve().parents[1]
    repo_root = api_dir.parents[1]
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    # Ensure API modules remain importable for DATABASE_URL / sqlmodel.
    api_str = str(api_dir)
    if api_str not in sys.path:
        sys.path.append(api_str)
    return repo_root


def run_weekly_pipeline(*, lookback_weeks: int = 2) -> None:
    """Synchronously run the weekly pipeline (no Prefect ephemeral server required)."""
    _ensure_repo_root_on_path()
    from data.pipelines.pipeline import run_weekly_pipeline_core

    logger.info(
        "Starting brasaland weekly location performance pipeline lookback_weeks=%s",
        lookback_weeks,
    )
    run_weekly_pipeline_core(
        lookback_weeks=lookback_weeks,
        use_prefect_engine=False,
    )
