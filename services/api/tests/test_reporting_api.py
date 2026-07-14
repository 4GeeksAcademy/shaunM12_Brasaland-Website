"""Smoke tests for reporting API wiring."""

from __future__ import annotations


def test_reporting_routes_require_auth(anon_client):
    assert anon_client.get("/reporting/weekly-location-performance").status_code == 401
    assert anon_client.get("/reporting/pipeline-runs/latest").status_code == 401
    assert anon_client.post("/reporting/pipeline-runs").status_code == 401


def test_pipeline_module_importable():
    from data.pipelines import pipeline as pipeline_mod
    from data.pipelines.blocks import (
        NIGHTLY_CRON_BOGOTA,
        BrasalandPipelineSettings,
        load_pipeline_settings,
    )

    assert pipeline_mod.FLOW_NAME == "brasaland_weekly_location_performance_pipeline"
    assert callable(pipeline_mod.brasaland_weekly_location_performance_pipeline)
    assert NIGHTLY_CRON_BOGOTA == "0 2 * * *"
    assert pipeline_mod.SCHEDULE_CRON == NIGHTLY_CRON_BOGOTA
    assert BrasalandPipelineSettings._block_type_name == "brasaland-pipeline-settings"
    settings = load_pipeline_settings()
    assert settings["lookback_weeks"] == 2
    assert settings["timezone"] == "America/Bogota"
