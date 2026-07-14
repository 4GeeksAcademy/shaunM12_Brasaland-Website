"""Smoke tests for reporting API wiring."""

from __future__ import annotations


def test_reporting_routes_require_auth(anon_client):
    assert anon_client.get("/reporting/weekly-location-performance").status_code == 401
    assert anon_client.get("/reporting/pipeline-runs/latest").status_code == 401
    assert anon_client.post("/reporting/pipeline-runs").status_code == 401


def test_pipeline_module_importable():
    from data.pipelines import pipeline as pipeline_mod

    assert pipeline_mod.FLOW_NAME == "brasaland_weekly_location_performance_pipeline"
    assert callable(pipeline_mod.brasaland_weekly_location_performance_pipeline)
