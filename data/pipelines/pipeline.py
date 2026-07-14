"""Brasaland weekly location performance Prefect pipeline (Milestone 6 Phase 2).

Schedule (document / deploy later): ~02:00 America/Bogota nightly.
CLI: ``python data/pipelines/pipeline.py`` from the repository root
     (or ``uv run`` from ``services/api`` with PYTHONPATH including repo root).

Prefect Blocks (optional; env fallbacks used locally):
- ``brasaland-postgres`` — connection string (else ``DATABASE_URL``)
- ``brasaland-pipeline-settings`` — lookback_weeks, timezone, paths
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# --- path bootstrap (repo-root ``data`` must win over ``services/api/data``) ---
_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_DIR = _REPO_ROOT / "services" / "api"
for _path in (str(_REPO_ROOT), str(_API_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from prefect import flow, task  # noqa: E402
from sqlalchemy import bindparam, text  # noqa: E402
from sqlmodel import Session  # noqa: E402

from data.process.weekly_location_kpis import (  # noqa: E402
    KPI_SOURCE_EVENT_TYPES,
    compute_weekly_kpis,
    extract_window_bounds,
)

logger = logging.getLogger(__name__)

FLOW_NAME = "brasaland_weekly_location_performance_pipeline"
DEFAULT_LOOKBACK_WEEKS = 2
DEFAULT_TIMEZONE = "America/Bogota"


def _load_database_url() -> str:
    """Resolve Postgres URL from Prefect block or environment."""
    try:
        from prefect.blocks.system import Secret

        secret = Secret.load("brasaland-postgres")
        value = secret.get()
        if value:
            return str(value)
    except Exception:  # noqa: BLE001 — local/dev without registered blocks
        logger.debug("brasaland-postgres block unavailable; using DATABASE_URL", exc_info=True)

    # Import config after path bootstrap so JWT check still works when .env present.
    try:
        import config as api_config

        url = getattr(api_config, "DATABASE_URL", None) or os.getenv("DATABASE_URL")
    except Exception:  # noqa: BLE001
        url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set and Prefect block brasaland-postgres is missing"
        )
    return str(url)


def _load_settings() -> dict[str, Any]:
    try:
        from prefect.blocks.system import JSON

        block = JSON.load("brasaland-pipeline-settings")
        raw = block.value if hasattr(block, "value") else block
        if isinstance(raw, dict):
            return {
                "lookback_weeks": int(
                    raw.get("lookback_weeks", DEFAULT_LOOKBACK_WEEKS)
                ),
                "timezone": str(raw.get("timezone", DEFAULT_TIMEZONE)),
                "raw_dir": str(raw.get("raw_dir", str(_REPO_ROOT / "data" / "raw"))),
                "eval_dir": str(raw.get("eval_dir", str(_REPO_ROOT / "data" / "eval"))),
            }
    except Exception:  # noqa: BLE001
        logger.debug(
            "brasaland-pipeline-settings block unavailable; using defaults",
            exc_info=True,
        )

    return {
        "lookback_weeks": int(
            os.getenv("PIPELINE_LOOKBACK_WEEKS", str(DEFAULT_LOOKBACK_WEEKS))
        ),
        "timezone": os.getenv("PIPELINE_TIMEZONE", DEFAULT_TIMEZONE),
        "raw_dir": os.getenv("PIPELINE_RAW_DIR", str(_REPO_ROOT / "data" / "raw")),
        "eval_dir": os.getenv("PIPELINE_EVAL_DIR", str(_REPO_ROOT / "data" / "eval")),
    }


def _session() -> Session:
    from database import get_engine
    from reporting.models import ensure_reporting_schema

    # Prefer URL from block over ambient engine when explicit.
    os.environ.setdefault("DATABASE_URL", _load_database_url())
    engine = get_engine()
    session = Session(engine)
    ensure_reporting_schema(session)
    return session


@task(retries=3, retry_delay_seconds=5, name="extract_telemetry_events")
def extract_telemetry_events(
    period_start: datetime,
    period_end: datetime,
    raw_dir: str,
) -> list[dict[str, Any]]:
    """Read KPI source events from telemetry_events for the extract window."""
    session = _session()
    try:
        statement = text(
            """
            SELECT id, event_type, timestamp, tags
            FROM telemetry_events
            WHERE event_type IN :event_types
              AND timestamp >= :period_start
              AND timestamp < :period_end
            """
        ).bindparams(bindparam("event_types", expanding=True))
        rows = session.execute(
            statement,
            {
                "event_types": KPI_SOURCE_EVENT_TYPES,
                "period_start": period_start,
                "period_end": period_end,
            },
        ).mappings().all()
        result = [dict(row) for row in rows]
        Path(raw_dir).mkdir(parents=True, exist_ok=True)
        stamp = period_start.strftime("%Y%m%dT%H%M%SZ")
        artifact = Path(raw_dir) / f"telemetry_extract_{stamp}.json"
        serializable = []
        for row in result:
            item = dict(row)
            ts = item.get("timestamp")
            if isinstance(ts, datetime):
                item["timestamp"] = ts.isoformat()
            serializable.append(item)
        artifact.write_text(json.dumps(serializable, default=str), encoding="utf-8")
        logger.info("Extracted %s events -> %s", len(result), artifact)
        return result
    finally:
        session.close()


def _purchase_cache_key(context, parameters: dict[str, Any]) -> str:  # type: ignore[no-untyped-def]
    """Cache key includes extract window + extract size (≤1h TTL on the task)."""
    period_start = parameters.get("period_start")
    period_end = parameters.get("period_end")
    n = len(parameters.get("rows") or [])
    return f"purchase-cost:{period_start}:{period_end}:{n}"


@task(
    name="transform_purchase_cost",
    cache_key_fn=_purchase_cache_key,
    cache_expiration=timedelta(hours=1),
)
def transform_purchase_cost_task(
    rows: list[dict[str, Any]],
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> dict[str, Any]:
    """Cached (≤1h) purchase-cost transform per design resilience section."""
    from data.process.weekly_location_kpis import (
        events_to_frame,
        transform_purchase_cost,
    )

    frame = events_to_frame(rows)
    purchase, skipped = transform_purchase_cost(frame)
    return {
        "records": purchase.to_dict(orient="records"),
        "skipped": skipped,
    }


@task(name="transform_waste_cost", retries=2, retry_delay_seconds=3)
def transform_waste_cost_task(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from data.process.weekly_location_kpis import events_to_frame, transform_waste_cost

    frame = events_to_frame(rows)
    waste, skipped = transform_waste_cost(frame)
    return {"records": waste.to_dict(orient="records"), "skipped": skipped}


@task(name="transform_waste_ratio")
def transform_waste_ratio_task(
    purchase_records: list[dict[str, Any]],
    waste_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    import pandas as pd

    from data.process.weekly_location_kpis import transform_waste_ratio

    purchase = pd.DataFrame(purchase_records)
    waste = pd.DataFrame(waste_records)
    return transform_waste_ratio(purchase, waste).to_dict(orient="records")


@task(name="transform_stockout_frequency")
def transform_stockout_frequency_task(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from data.process.weekly_location_kpis import (
        events_to_frame,
        transform_stockout_frequency,
    )

    return transform_stockout_frequency(events_to_frame(rows)).to_dict(orient="records")


@task(name="transform_price_alert_frequency")
def transform_price_alert_frequency_task(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    from data.process.weekly_location_kpis import (
        events_to_frame,
        transform_price_alert_frequency,
    )

    return transform_price_alert_frequency(events_to_frame(rows)).to_dict(
        orient="records"
    )


@task(name="load_weekly_location_performance", retries=3, retry_delay_seconds=5)
def load_weekly_location_performance(
    rows: list[dict[str, Any]],
) -> int:
    from reporting.repository import upsert_weekly_rows

    session = _session()
    try:
        # Normalize week_start from ISO strings if needed.
        normalized = []
        for row in rows:
            item = dict(row)
            ws = item.get("week_start")
            if isinstance(ws, str):
                item["week_start"] = date.fromisoformat(ws[:10])
            normalized.append(item)
        return upsert_weekly_rows(session, normalized)
    finally:
        session.close()


@task(name="record_pipeline_run")
def record_pipeline_run(
    run_id: str,
    *,
    status: str,
    records_extracted: int,
    records_loaded: int,
    records_skipped_missing_cost: int,
    errors: dict[str, Any] | None = None,
) -> None:
    import uuid

    from reporting.repository import finish_pipeline_run

    session = _session()
    try:
        finish_pipeline_run(
            session,
            uuid.UUID(run_id),
            status=status,
            records_extracted=records_extracted,
            records_loaded=records_loaded,
            records_skipped_missing_cost=records_skipped_missing_cost,
            errors=errors,
        )
    finally:
        session.close()


@flow(name="export_pipeline_eval_flow")
def export_pipeline_eval_flow(
    eval_dir: str,
    kpi_rows: list[dict[str, Any]],
    meta: dict[str, Any],
) -> str:
    """Optional eval export — parent invokes with return_state=True when using Prefect engine."""
    Path(eval_dir).mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = Path(eval_dir) / f"weekly_location_performance_{stamp}.json"
    path.write_text(
        json.dumps({"meta": meta, "rows": kpi_rows}, default=str, indent=2),
        encoding="utf-8",
    )
    return str(path)


def run_weekly_pipeline_core(
    lookback_weeks: int | None = None,
    *,
    use_prefect_engine: bool = False,
) -> dict[str, Any]:
    """Extract → transform → load → audit.

    ``use_prefect_engine=True`` runs Prefect tasks/subflows (needs API/ephemeral server).
    Default ``False`` uses ``.fn()`` so CLI / FastAPI background work without a Prefect server.
    """
    settings = _load_settings()
    weeks = lookback_weeks if lookback_weeks is not None else settings["lookback_weeks"]
    period_start, period_end, week_starts = extract_window_bounds(lookback_weeks=weeks)

    from reporting.repository import start_pipeline_run

    def _call(task_or_fn, *args, **kwargs):
        if use_prefect_engine:
            return task_or_fn(*args, **kwargs)
        return task_or_fn.fn(*args, **kwargs)

    session = _session()
    try:
        run_id = start_pipeline_run(
            session,
            flow_name=FLOW_NAME,
            week_start=week_starts[-1] if week_starts else None,
            period_start=period_start,
            period_end=period_end,
        )
    finally:
        session.close()

    extracted = 0
    loaded = 0
    skipped = 0
    try:
        rows = _call(
            extract_telemetry_events,
            period_start,
            period_end,
            settings["raw_dir"],
        )
        extracted = len(rows)

        purchase_result = _call(
            transform_purchase_cost_task,
            rows,
            period_start=period_start,
            period_end=period_end,
        )
        waste_result = _call(transform_waste_cost_task, rows)
        skipped = int(purchase_result["skipped"]) + int(waste_result["skipped"])
        if skipped:
            logger.warning(
                "Skipped %s events missing quantity/unit_cost for cost KPIs", skipped
            )

        ratio_records = _call(
            transform_waste_ratio_task,
            purchase_result["records"],
            waste_result["records"],
        )
        stockout_records = _call(transform_stockout_frequency_task, rows)
        price_records = _call(transform_price_alert_frequency_task, rows)

        kpi_frame, skipped_total = compute_weekly_kpis(rows, week_starts=week_starts)
        skipped = skipped_total
        kpi_rows = kpi_frame.to_dict(orient="records")
        _ = (ratio_records, stockout_records, price_records)

        loaded = _call(load_weekly_location_performance, kpi_rows)

        export_meta = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "week_starts": [w.isoformat() for w in week_starts],
            "records_skipped_missing_cost": skipped,
        }
        if use_prefect_engine:
            # Optional export must not fail the main run.
            export_pipeline_eval_flow(
                settings["eval_dir"],
                kpi_rows,
                export_meta,
                return_state=True,
            )
        else:
            try:
                export_pipeline_eval_flow.fn(
                    settings["eval_dir"], kpi_rows, export_meta
                )
            except Exception:  # noqa: BLE001
                logger.exception("Eval export failed; continuing main pipeline")

        _call(
            record_pipeline_run,
            str(run_id),
            status="completed",
            records_extracted=extracted,
            records_loaded=loaded,
            records_skipped_missing_cost=skipped,
        )
        return {
            "status": "completed",
            "run_id": str(run_id),
            "records_extracted": extracted,
            "records_loaded": loaded,
            "records_skipped_missing_cost": skipped,
            "week_starts": [w.isoformat() for w in week_starts],
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed")
        record_pipeline_run.fn(
            str(run_id),
            status="failed",
            records_extracted=extracted,
            records_loaded=loaded,
            records_skipped_missing_cost=skipped,
            errors={"message": str(exc)},
        )
        raise


@flow(name=FLOW_NAME)
def brasaland_weekly_location_performance_pipeline(
    lookback_weeks: int | None = None,
) -> dict[str, Any]:
    """Prefect-engine entry (scheduler / `flow()` calls). Prefer CLI via ``main()``."""
    return run_weekly_pipeline_core(
        lookback_weeks=lookback_weeks,
        use_prefect_engine=True,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # Avoid ephemeral Prefect API server for local CLI (Module import still needs venv).
    result = run_weekly_pipeline_core(use_prefect_engine=False)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
