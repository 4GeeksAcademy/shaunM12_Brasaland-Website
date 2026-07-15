"""Prefect Blocks for Brasaland weekly location performance pipeline.

Register once (optional; env fallbacks work without this):

    uv run python -c \"from data.pipelines.blocks import save_default_blocks; save_default_blocks()\"

Block names (locked):
- brasaland-postgres
- brasaland-pipeline-settings
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from prefect.blocks.core import Block
from prefect.blocks.system import Secret
from pydantic import Field

_REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_LOOKBACK_WEEKS = 2
DEFAULT_TIMEZONE = "America/Bogota"
# Prefect cron (minute hour day month weekday). Deploy when a worker is available.
NIGHTLY_CRON_BOGOTA = "0 2 * * *"  # ~02:00 America/Bogota


class BrasalandPipelineSettings(Block):
    """Settings block registered as ``brasaland-pipeline-settings``."""

    _block_type_name = "brasaland-pipeline-settings"
    _logo_url = None

    lookback_weeks: int = Field(default=DEFAULT_LOOKBACK_WEEKS, ge=1, le=8)
    timezone: str = Field(default=DEFAULT_TIMEZONE)
    raw_dir: str = Field(default=str(_REPO_ROOT / "data" / "raw"))
    eval_dir: str = Field(default=str(_REPO_ROOT / "data" / "eval"))
    schedule_cron: str = Field(
        default=NIGHTLY_CRON_BOGOTA,
        description="Nightly recompute cron (~02:00 America/Bogota)",
    )


def settings_as_dict(settings: BrasalandPipelineSettings | dict[str, Any]) -> dict[str, Any]:
    if isinstance(settings, BrasalandPipelineSettings):
        return {
            "lookback_weeks": settings.lookback_weeks,
            "timezone": settings.timezone,
            "raw_dir": settings.raw_dir,
            "eval_dir": settings.eval_dir,
            "schedule_cron": settings.schedule_cron,
        }
    return dict(settings)


def load_pipeline_settings() -> dict[str, Any]:
    """Prefer named Blocks; fall back to env / defaults for local CLI."""
    try:
        loaded = BrasalandPipelineSettings.load("brasaland-pipeline-settings")
        return settings_as_dict(loaded)
    except Exception:
        pass

    return {
        "lookback_weeks": int(
            os.getenv("PIPELINE_LOOKBACK_WEEKS", str(DEFAULT_LOOKBACK_WEEKS))
        ),
        "timezone": os.getenv("PIPELINE_TIMEZONE", DEFAULT_TIMEZONE),
        "raw_dir": os.getenv("PIPELINE_RAW_DIR", str(_REPO_ROOT / "data" / "raw")),
        "eval_dir": os.getenv("PIPELINE_EVAL_DIR", str(_REPO_ROOT / "data" / "eval")),
        "schedule_cron": os.getenv("PIPELINE_SCHEDULE_CRON", NIGHTLY_CRON_BOGOTA),
    }


def load_database_url() -> str:
    try:
        secret = Secret.load("brasaland-postgres")
        value = secret.get()
        if value:
            return str(value)
    except Exception:
        pass

    try:
        import config as api_config

        url = getattr(api_config, "DATABASE_URL", None) or os.getenv("DATABASE_URL")
    except Exception:
        url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set and Prefect block brasaland-postgres is missing"
        )
    return str(url)


def save_default_blocks(*, database_url: str | None = None) -> None:
    """Persist default Blocks locally / to the active Prefect profile."""
    url = database_url or os.getenv("DATABASE_URL")
    if url:
        Secret(value=url).save("brasaland-postgres", overwrite=True)

    BrasalandPipelineSettings(
        lookback_weeks=DEFAULT_LOOKBACK_WEEKS,
        timezone=DEFAULT_TIMEZONE,
        raw_dir=str(_REPO_ROOT / "data" / "raw"),
        eval_dir=str(_REPO_ROOT / "data" / "eval"),
        schedule_cron=NIGHTLY_CRON_BOGOTA,
    ).save("brasaland-pipeline-settings", overwrite=True)
