"""Ensure the monorepo ``data`` package is importable from the API process."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _rag_pipeline_marker(root: Path) -> Path:
    return root / "data" / "pipelines" / "rag.py"


def ensure_repo_root_on_path() -> Path:
    """Prefer repo-root ``data`` over ``services/api/data`` TinyDB dir.

    Local: ``<repo>/services/api`` → parents[1] is the repo.
    Docker: ``BRASALAND_REPO_ROOT`` (default ``/workspace``) with ``./data`` mounted.
    """
    api_dir = Path(__file__).resolve().parents[1]
    env_root = os.environ.get("BRASALAND_REPO_ROOT", "").strip()
    candidates: list[Path] = []
    if env_root:
        candidates.append(Path(env_root))
    if len(api_dir.parents) > 1:
        candidates.append(api_dir.parents[1])
    candidates.append(Path("/workspace"))

    repo_root: Path | None = None
    for candidate in candidates:
        root = candidate.resolve()
        if _rag_pipeline_marker(root).is_file():
            repo_root = root
            break

    if repo_root is None:
        searched = ", ".join(str(c) for c in candidates)
        raise RuntimeError(
            "Could not locate data/pipelines/rag.py. "
            f"Searched: {searched}. "
            "Mount ./data into the container and/or set BRASALAND_REPO_ROOT."
        )

    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    api_str = str(api_dir)
    if api_str not in sys.path:
        sys.path.append(api_str)
    return repo_root
