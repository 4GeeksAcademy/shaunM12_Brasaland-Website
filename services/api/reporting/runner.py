"""Background runner that invokes the Prefect weekly pipeline."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _pipeline_marker(root: Path) -> Path:
    return root / "data" / "pipelines" / "pipeline.py"


def _ensure_repo_root_on_path() -> Path:
    """Prefer repo-root ``data`` package over ``services/api/data`` TinyDB dir.

    Local monorepo layout: ``<repo>/services/api/...`` → repo is ``api_dir.parents[1]``.
    Docker mounts ``./data`` at ``$BRASALAND_REPO_ROOT/data`` (default ``/workspace``).
    """
    api_dir = Path(__file__).resolve().parents[1]
    env_root = os.environ.get("BRASALAND_REPO_ROOT", "").strip()
    candidates: list[Path] = []
    if env_root:
        candidates.append(Path(env_root))
    # Monorepo: <repo>/services/api — only when path is deep enough (not Docker /app).
    if len(api_dir.parents) > 1:
        candidates.append(api_dir.parents[1])
    candidates.append(Path("/workspace"))

    repo_root: Path | None = None
    for candidate in candidates:
        root = candidate.resolve()
        if _pipeline_marker(root).is_file():
            repo_root = root
            break

    if repo_root is None:
        searched = ", ".join(str(c) for c in candidates)
        raise RuntimeError(
            "Could not locate data/pipelines/pipeline.py. "
            f"Searched: {searched}. "
            "Mount ./data into the container and/or set BRASALAND_REPO_ROOT."
        )

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
    try:
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
        logger.info("Weekly location performance pipeline finished")
    except Exception:
        logger.exception("Weekly location performance pipeline failed")
        raise
