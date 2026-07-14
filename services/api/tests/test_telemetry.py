"""Unit tests for the telemetry module (no Supabase required)."""

from __future__ import annotations

import importlib
import json
import logging

import config
import pytest

from telemetry.constants import currency_for_location, load_event_schemas
from telemetry.context import EmitContext
from telemetry.dedupe import clear_threshold_dedupe, should_emit_threshold_crossing
from telemetry.emit import TelemetryValidationError, build_envelope, emit_event


def test_load_event_schemas_has_wave_1_inventory_events():
    load_event_schemas.cache_clear()
    schemas = load_event_schemas()
    inventory = schemas["domains"]["inventory"]["events"]
    assert "outbound_order_created" in inventory
    assert "stock_waste_registered" in inventory
    assert "inbound_order_created" in inventory
    assert "stock_threshold_triggered" in inventory
    assert "direct_stock_edit_rejected" in inventory
    assert "ingredient_price_variance_detected" in inventory


def test_currency_for_location():
    assert currency_for_location(1) == "COP"
    assert currency_for_location(9) == "COP"
    assert currency_for_location(10) == "USD"
    assert currency_for_location(14) == "USD"


def test_build_envelope_injects_currency_and_country():
    ctx = EmitContext(user_id="usr_test", session_id="sess_test", request_id="req_test")
    envelope = build_envelope(
        "outbound_order_created",
        {
            "outbound_order_id": 1,
            "product_id": 2,
            "product_category": "meat",
            "quantity": 3.0,
            "location_id": 11,
            "created_by": "usr_test",
            "unit": "kg",
        },
        ctx,
    )
    assert envelope["properties"]["currency"] == "USD"
    assert envelope["properties"]["country"] == "US"
    assert envelope["event_type"] == "outbound_order_created"
    assert envelope["schemaVersion"] == 2
    assert envelope["userId"] == "usr_test"


def test_build_envelope_rejects_extra_properties():
    ctx = EmitContext()
    with pytest.raises(TelemetryValidationError, match="unknown properties"):
        build_envelope(
            "direct_stock_edit_rejected",
            {
                "attempted_field": "current_stock",
                "rejection_reason": "direct_stock_mutation_forbidden",
                "http_method": "PATCH",
                "http_path": "/inventory/products/1",
                "unexpected_key": True,
            },
            ctx,
        )


def test_emit_event_disabled_returns_none(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "TELEMETRY_ENABLED", False)
    result = emit_event(
        "outbound_order_created",
        {
            "outbound_order_id": 1,
            "product_id": 1,
            "product_category": "meat",
            "quantity": 1.0,
            "location_id": 1,
            "created_by": "usr",
            "unit": "kg",
        },
    )
    assert result is None


def test_emit_event_stdout_when_enabled(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    import telemetry.emit as emit_module

    importlib.reload(emit_module)
    monkeypatch.setattr(config, "TELEMETRY_ENABLED", True)
    monkeypatch.setattr(config, "TELEMETRY_SINK", "stdout")

    with caplog.at_level(logging.INFO, logger="brasaland.telemetry"):
        envelope = emit_event(
            "outbound_order_created",
            {
                "outbound_order_id": 99,
                "product_id": 7,
                "product_category": "meat",
                "quantity": 2.5,
                "location_id": 3,
                "created_by": "usr_abc",
                "unit": "kg",
            },
            ctx=EmitContext(user_id="usr_abc"),
        )

    assert envelope is not None
    assert envelope["properties"]["currency"] == "COP"
    assert envelope["properties"]["country"] == "CO"
    assert any("telemetry_event" in record.message for record in caplog.records)
    logged = next(r for r in caplog.records if "telemetry_event" in r.message)
    payload = json.loads(logged.message.split("telemetry_event ", 1)[1])
    assert payload["event_type"] == "outbound_order_created"


def test_threshold_edge_trigger_and_dedupe():
    clear_threshold_dedupe()
    assert should_emit_threshold_crossing(
        ingredient_id=1,
        location_id=1,
        stock_before=15.0,
        stock_after=9.0,
        threshold=10.0,
    )
    from telemetry.dedupe import record_threshold_emission

    record_threshold_emission(ingredient_id=1, location_id=1)
    assert not should_emit_threshold_crossing(
        ingredient_id=1,
        location_id=1,
        stock_before=9.0,
        stock_after=8.0,
        threshold=10.0,
    )
    assert should_emit_threshold_crossing(
        ingredient_id=1,
        location_id=1,
        stock_before=8.0,
        stock_after=15.0,
        threshold=10.0,
    ) is False
    assert should_emit_threshold_crossing(
        ingredient_id=1,
        location_id=1,
        stock_before=15.0,
        stock_after=9.0,
        threshold=10.0,
    )
