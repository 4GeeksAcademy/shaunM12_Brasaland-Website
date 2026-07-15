"""Phase 3 pipeline tests: subflows, transforms, missing-cost skip, upsert grain uniqueness."""

from __future__ import annotations

from datetime import date, datetime, timezone

from data.pipelines import pipeline as pipeline_mod
from data.process.weekly_location_kpis import (
    compute_weekly_kpis,
    transform_purchase_cost,
    events_to_frame,
)


def test_phase3_subflow_names_locked():
    assert pipeline_mod.extract_telemetry_events_flow.name == "extract_telemetry_events_flow"
    assert (
        pipeline_mod.transform_weekly_location_performance_flow.name
        == "transform_weekly_location_performance_flow"
    )
    assert (
        pipeline_mod.load_weekly_location_performance_flow.name
        == "load_weekly_location_performance_flow"
    )
    assert pipeline_mod.export_pipeline_eval_flow.name == "export_pipeline_eval_flow"
    assert (
        pipeline_mod.brasaland_weekly_location_performance_pipeline.name
        == "brasaland_weekly_location_performance_pipeline"
    )


def test_happy_path_transform_produces_five_kpi_fields():
    rows = [
        {
            "id": 1,
            "event_type": "inbound_order_created",
            "timestamp": datetime(2026, 7, 14, 10, tzinfo=timezone.utc),
            "tags": {
                "location_id": 1,
                "country": "CO",
                "currency": "COP",
                "quantity": 10,
                "unit_cost": 100,
            },
        },
        {
            "id": 2,
            "event_type": "stock_waste_registered",
            "timestamp": datetime(2026, 7, 14, 11, tzinfo=timezone.utc),
            "tags": {
                "location_id": 1,
                "country": "CO",
                "currency": "COP",
                "quantity": 2,
                "unit_cost": 100,
            },
        },
        {
            "id": 3,
            "event_type": "stock_threshold_triggered",
            "timestamp": datetime(2026, 7, 14, 12, tzinfo=timezone.utc),
            "tags": {"location_id": 1, "country": "CO", "currency": "COP"},
        },
        {
            "id": 4,
            "event_type": "ingredient_price_variance_detected",
            "timestamp": datetime(2026, 7, 14, 13, tzinfo=timezone.utc),
            "tags": {"location_id": 1, "country": "CO", "currency": "COP"},
        },
    ]
    frame, skipped = compute_weekly_kpis(rows)
    assert skipped == 0
    assert len(frame) == 1
    row = frame.iloc[0]
    assert float(row["total_purchase_cost"]) == 1000.0
    assert float(row["total_waste_cost"]) == 200.0
    assert float(row["waste_ratio"]) == 0.2
    assert int(row["stockout_events_count"]) == 1
    assert int(row["price_alert_events_count"]) == 1


def test_missing_unit_cost_skipped_from_cost_kpis():
    rows = [
        {
            "id": 1,
            "event_type": "inbound_order_created",
            "timestamp": datetime(2026, 7, 14, 10, tzinfo=timezone.utc),
            "tags": {"location_id": 2, "quantity": 5, "unit_cost": 10},
        },
        {
            "id": 2,
            "event_type": "inbound_order_created",
            "timestamp": datetime(2026, 7, 14, 11, tzinfo=timezone.utc),
            "tags": {"location_id": 2, "quantity": 5},  # missing unit_cost
        },
        {
            "id": 3,
            "event_type": "stock_waste_registered",
            "timestamp": datetime(2026, 7, 14, 12, tzinfo=timezone.utc),
            "tags": {"location_id": 2, "quantity": 1},  # missing unit_cost
        },
    ]
    frame, skipped = compute_weekly_kpis(rows)
    assert skipped == 2
    assert float(frame.iloc[0]["total_purchase_cost"]) == 50.0
    assert float(frame.iloc[0]["total_waste_cost"]) == 0.0


def test_upsert_grain_uniqueness_in_kpi_output():
    """Two transform passes over the same events yield one grain per location/week."""
    rows = [
        {
            "id": 1,
            "event_type": "stock_threshold_triggered",
            "timestamp": datetime(2026, 7, 15, 10, tzinfo=timezone.utc),
            "tags": {"location_id": 5, "country": "CO", "currency": "COP"},
        }
    ]
    first, _ = compute_weekly_kpis(rows)
    second, _ = compute_weekly_kpis(rows)
    merged = first.to_dict(orient="records") + second.to_dict(orient="records")
    grains = {(int(r["location_id"]), str(r["week_start"])) for r in merged}
    assert len(grains) == 1
    assert grains == {(5, "2026-07-13")}


def test_transform_purchase_cost_unit():
    rows = [
        {
            "id": 1,
            "event_type": "inbound_order_created",
            "timestamp": datetime(2026, 7, 13, 1, tzinfo=timezone.utc),
            "tags": {"location_id": 11, "quantity": 4, "unit_cost": 2.5},
        }
    ]
    purchase, skipped = transform_purchase_cost(events_to_frame(rows))
    assert skipped == 0
    assert float(purchase.iloc[0]["total_purchase_cost"]) == 10.0
    assert purchase.iloc[0]["currency"] == "USD"


def test_transform_subflow_fn_path():
    """Thin Phase 3 transform subflow runs without Prefect ephemeral server."""
    rows = [
        {
            "id": 1,
            "event_type": "inbound_order_created",
            "timestamp": datetime(2026, 7, 14, 10, tzinfo=timezone.utc),
            "tags": {
                "location_id": 1,
                "country": "CO",
                "currency": "COP",
                "quantity": 1,
                "unit_cost": 50,
            },
        }
    ]
    week_starts = [date(2026, 7, 13)]
    period_start = datetime(2026, 7, 13, tzinfo=timezone.utc)
    period_end = datetime(2026, 7, 20, tzinfo=timezone.utc)
    result = pipeline_mod.transform_weekly_location_performance_flow.fn(
        rows,
        week_starts,
        period_start,
        period_end,
        use_engine=False,
    )
    assert result["skipped"] == 0
    assert len(result["kpi_rows"]) == 1
    assert float(result["kpi_rows"][0]["total_purchase_cost"]) == 50.0
