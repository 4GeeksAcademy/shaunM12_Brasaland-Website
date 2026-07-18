"""Smoke tests for reporting API wiring."""

from __future__ import annotations


def test_reporting_routes_require_auth(anon_client):
    assert anon_client.get("/reporting/weekly-location-performance").status_code == 401
    assert anon_client.get("/reporting/pipeline-runs/latest").status_code == 401
    assert anon_client.post("/reporting/pipeline-runs").status_code == 401


def test_tasks_route_requires_auth(anon_client):
    assert anon_client.get("/tasks/fake-task-id").status_code == 401


def test_map_celery_state():
    from tasks.routes import map_celery_state

    assert map_celery_state("PENDING") == "pending"
    assert map_celery_state("STARTED") == "started"
    assert map_celery_state("SUCCESS") == "success"
    assert map_celery_state("FAILURE") == "failure"
    assert map_celery_state("RETRY") == "pending"
    assert map_celery_state("REVOKED") == "failure"


def test_pipeline_enqueue_returns_task_id(client, monkeypatch):
    class _FakeResult:
        id = "test-task-id-123"

    monkeypatch.setattr(
        "reporting.routes.run_weekly_pipeline_task.delay",
        lambda lookback_weeks=2: _FakeResult(),
    )
    response = client.post("/reporting/pipeline-runs")
    assert response.status_code == 202
    body = response.json()
    assert body["task_id"] == "test-task-id-123"
    assert body["status"] == "accepted"
    assert "message" in body


def test_pipeline_module_importable():
    from data.pipelines import pipeline as pipeline_mod
    from data.pipelines.blocks import (
        NIGHTLY_CRON_BOGOTA,
        BrasalandPipelineSettings,
        load_pipeline_settings,
    )

    assert pipeline_mod.FLOW_NAME == "brasaland_weekly_location_performance_pipeline"
    assert callable(pipeline_mod.brasaland_weekly_location_performance_pipeline)
    assert pipeline_mod.extract_telemetry_events_flow.name == "extract_telemetry_events_flow"
    assert NIGHTLY_CRON_BOGOTA == "0 2 * * *"
    assert pipeline_mod.SCHEDULE_CRON == NIGHTLY_CRON_BOGOTA
    assert BrasalandPipelineSettings._block_type_name == "brasaland-pipeline-settings"
    settings = load_pipeline_settings()
    assert settings["lookback_weeks"] == 2
    assert settings["timezone"] == "America/Bogota"
