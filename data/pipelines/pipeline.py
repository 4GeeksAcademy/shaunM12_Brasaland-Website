"""Brasaland weekly location performance Prefect pipeline (Milestone 6 Phase 2).

Schedule: nightly ~02:00 America/Bogota (``NIGHTLY_CRON_BOGOTA = "0 2 * * *"``).
CLI (recommended)::

    cd services/api && uv run python ../../data/pipelines/pipeline.py

Prefect Blocks (see ``data/pipelines/blocks.py``):
- ``brasaland-postgres`` — connection string (else ``DATABASE_URL``)
- ``brasaland-pipeline-settings`` — lookback_weeks, timezone, paths, schedule_cron
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

from data.pipelines.blocks import (  # noqa: E402
    NIGHTLY_CRON_BOGOTA,
    load_database_url,
    load_pipeline_settings,
)
from data.process.weekly_location_kpis import (  # noqa: E402
    KPI_SOURCE_EVENT_TYPES,
    compute_weekly_kpis,
    extract_window_bounds,
)

logger = logging.getLogger(__name__)

FLOW_NAME = "brasaland_weekly_location_performance_pipeline"
DEFAULT_LOOKBACK_WEEKS = 2
DEFAULT_TIMEZONE = "America/Bogota"
SCHEDULE_CRON = NIGHTLY_CRON_BOGOTA


def _load_database_url() -> str:
    return load_database_url()


def _load_settings() -> dict[str, Any]:
    return load_pipeline_settings()


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


def _invoke(fn: Any, run_with_engine: bool, *args: Any, **kwargs: Any) -> Any:
    """Call a Prefect task/flow with or without the orchestration engine."""
    if run_with_engine:
        return fn(*args, **kwargs)
    return fn.fn(*args, **kwargs)


@flow(name="extract_telemetry_events_flow")
def extract_telemetry_events_flow(
    period_start: datetime,
    period_end: datetime,
    raw_dir: str,
    *,
    use_engine: bool = True,
) -> list[dict[str, Any]]:
    """Phase 3 extract subflow — thin wrapper around extract_telemetry_events task."""
    return _invoke(
        extract_telemetry_events,
        use_engine,
        period_start,
        period_end,
        raw_dir,
    )


@flow(name="transform_weekly_location_performance_flow")
def transform_weekly_location_performance_flow(
    rows: list[dict[str, Any]],
    week_starts: list[date],
    period_start: datetime,
    period_end: datetime,
    *,
    use_engine: bool = True,
) -> dict[str, Any]:
    """Phase 3 transform subflow — runs the five KPI tasks, then sparse merge."""
    purchase_result = _invoke(
        transform_purchase_cost_task,
        use_engine,
        rows,
        period_start=period_start,
        period_end=period_end,
    )
    waste_result = _invoke(transform_waste_cost_task, use_engine, rows)
    skipped = int(purchase_result["skipped"]) + int(waste_result["skipped"])
    if skipped:
        logger.warning(
            "Skipped %s events missing quantity/unit_cost for cost KPIs", skipped
        )

    ratio_records = _invoke(
        transform_waste_ratio_task,
        use_engine,
        purchase_result["records"],
        waste_result["records"],
    )
    stockout_records = _invoke(
        transform_stockout_frequency_task, use_engine, rows
    )
    price_records = _invoke(
        transform_price_alert_frequency_task, use_engine, rows
    )

    kpi_frame, skipped_total = compute_weekly_kpis(rows, week_starts=week_starts)
    _ = (ratio_records, stockout_records, price_records)
    return {
        "kpi_rows": kpi_frame.to_dict(orient="records"),
        "skipped": skipped_total,
    }


@flow(name="load_weekly_location_performance_flow")
def load_weekly_location_performance_flow(
    kpi_rows: list[dict[str, Any]],
    run_id: str,
    *,
    records_extracted: int,
    records_skipped_missing_cost: int,
    use_engine: bool = True,
) -> int:
    """Phase 3 load subflow — upsert KPI grains and finish pipeline_runs audit."""
    loaded = _invoke(load_weekly_location_performance, use_engine, kpi_rows)
    _invoke(
        record_pipeline_run,
        use_engine,
        run_id,
        status="completed",
        records_extracted=records_extracted,
        records_loaded=loaded,
        records_skipped_missing_cost=records_skipped_missing_cost,
    )
    return loaded


def run_weekly_pipeline_core(
    lookback_weeks: int | None = None,
    *,
    use_prefect_engine: bool = False,
) -> dict[str, Any]:
    """Extract → transform → load → audit via named Phase 3 subflows.

    ``use_prefect_engine=True`` runs Prefect tasks/subflows (needs API/ephemeral server).
    Default ``False`` uses ``.fn()`` so CLI / FastAPI background work without a Prefect server.
    """
    settings = _load_settings()
    weeks = lookback_weeks if lookback_weeks is not None else settings["lookback_weeks"]
    period_start, period_end, week_starts = extract_window_bounds(lookback_weeks=weeks)

    from reporting.repository import start_pipeline_run

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
        rows = _invoke(
            extract_telemetry_events_flow,
            use_prefect_engine,
            period_start,
            period_end,
            settings["raw_dir"],
            use_engine=use_prefect_engine,
        )
        extracted = len(rows)

        transform_result = _invoke(
            transform_weekly_location_performance_flow,
            use_prefect_engine,
            rows,
            week_starts,
            period_start,
            period_end,
            use_engine=use_prefect_engine,
        )
        kpi_rows = transform_result["kpi_rows"]
        skipped = int(transform_result["skipped"])

        loaded = _invoke(
            load_weekly_location_performance_flow,
            use_prefect_engine,
            kpi_rows,
            str(run_id),
            records_extracted=extracted,
            records_skipped_missing_cost=skipped,
            use_engine=use_prefect_engine,
        )

        export_meta = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "week_starts": [w.isoformat() for w in week_starts],
            "records_skipped_missing_cost": skipped,
        }
        if use_prefect_engine:
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
    """Prefect-engine entry — composes extract/transform/load subflows."""
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
