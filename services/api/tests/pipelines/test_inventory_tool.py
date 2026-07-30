"""Unit tests for inventory lookup tool (mocked HTTP — P2-L9, P2-L12)."""

from __future__ import annotations

import pytest

from agent.tools import inventory as inventory_mod


def _sample_product(product_id: int = 1) -> dict:
    return {
        "id": product_id,
        "name": "Beef brisket",
        "sku": "BRS-BEEF-001",
        "unit": "kg",
        "category": "meat",
        "country": "CO",
        "is_active": True,
        "current_stock": 50.0,
        "min_stock_threshold": 40.0,
    }


def test_extract_inventory_hints_sku():
    hints = inventory_mod.extract_inventory_hints("Current stock for SKU BEEF-001")
    assert hints["sku"] == "BEEF-001"


def test_lookup_inventory_by_sku_filters_list(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    def _fetch(method, path, *, params=None, headers=None, timeout=None):
        captured["method"] = method
        captured["path"] = path
        captured["headers"] = headers
        return 200, [_sample_product(), {"id": 2, "sku": "BRS-CHICK-001", "name": "Chicken"}], None

    monkeypatch.setattr(inventory_mod, "fetch_json", _fetch)

    envelope = inventory_mod.lookup_inventory_stock(
        question="Current stock for SKU BEEF-001",
        auth_header="Bearer test-token",
    )

    assert envelope["ok"] is True
    assert len(envelope["rows"]) == 1
    assert envelope["rows"][0]["sku"] == "BRS-BEEF-001"
    assert envelope["filters"]["sku"] == "BEEF-001"
    assert captured["path"] == "/inventory/products"
    assert captured["headers"]["Authorization"] == "Bearer test-token"


def test_lookup_inventory_product_detail(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    def _fetch(method, path, *, params=None, headers=None, timeout=None):
        captured["path"] = path
        captured["params"] = params
        return 200, _sample_product(7), None

    monkeypatch.setattr(inventory_mod, "fetch_json", _fetch)

    envelope = inventory_mod.lookup_inventory_stock(
        question="What is product 7 stock at location 1?",
        auth_header=None,
    )

    assert envelope["ok"] is True
    assert envelope["rows"][0]["id"] == 7
    assert envelope["rows"][0]["location_id"] == 1
    assert captured["path"] == "/inventory/products/7"
    assert captured["params"] == {"location_id": 1}


def test_lookup_inventory_empty_sku_match(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        inventory_mod,
        "fetch_json",
        lambda *a, **k: (200, [_sample_product()], None),
    )

    envelope = inventory_mod.lookup_inventory_stock(
        question="Current stock for SKU UNKNOWN-999",
        auth_header=None,
    )

    assert envelope["ok"] is True
    assert envelope["reason"] == "empty"
    assert envelope["rows"] == []


def test_lookup_inventory_not_found(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        inventory_mod,
        "fetch_json",
        lambda *a, **k: (404, {"detail": "Product not found"}, None),
    )

    envelope = inventory_mod.lookup_inventory_stock(
        question="Stock for product 999",
        auth_header="Bearer t",
    )

    assert envelope["ok"] is False
    assert envelope["reason"] == "not_found"


def test_lookup_inventory_timeout(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        inventory_mod,
        "fetch_json",
        lambda *a, **k: (0, None, "timeout"),
    )

    envelope = inventory_mod.lookup_inventory_stock(
        question="Current stock for SKU BEEF-001",
        auth_header=None,
    )

    assert envelope["ok"] is False
    assert envelope["reason"] == "timeout"
