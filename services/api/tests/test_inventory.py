"""Inventory API tests (Supabase + dual-database)."""

from __future__ import annotations

import uuid

import config
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    not config.DATABASE_URL,
    reason="DATABASE_URL not set — inventory tests require Supabase",
)


def _unique_sku() -> str:
    return f"TEST-{uuid.uuid4().hex[:8].upper()}"


def test_list_products_includes_computed_stock(anon_client: TestClient):
    resp = anon_client.get("/inventory/products")
    assert resp.status_code == 200
    products = resp.json()
    assert len(products) >= 6
    beef = next(p for p in products if p["sku"] == "BRS-BEEF-001")
    # Seeded: 50 + 30 inbound, 25 + 5 outbound => 50 kg
    assert beef["current_stock"] == 50.0
    assert beef["country"] == "CO"


def test_create_product_requires_auth(anon_client: TestClient):
    resp = anon_client.post(
        "/inventory/products",
        json={
            "name": "Unauthorized",
            "sku": _unique_sku(),
            "unit": "kg",
            "category": "meat",
            "country": "CO",
        },
    )
    assert resp.status_code == 401


def test_create_product_starts_at_zero_stock(auth_client: TestClient):
    sku = _unique_sku()
    resp = auth_client.post(
        "/inventory/products",
        json={
            "name": "Test ingredient",
            "sku": sku,
            "unit": "kg",
            "category": "meat",
            "country": "CO",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["sku"] == sku
    assert body["current_stock"] == 0.0


def test_get_product_by_id(auth_client: TestClient):
    sku = _unique_sku()
    created = auth_client.post(
        "/inventory/products",
        json={
            "name": "Lookup test",
            "sku": sku,
            "unit": "unit",
            "category": "packaging",
            "country": "US",
        },
    ).json()
    resp = auth_client.get(f"/inventory/products/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["sku"] == sku


def test_duplicate_sku_rejected(auth_client: TestClient):
    sku = _unique_sku()
    payload = {
        "name": "First",
        "sku": sku,
        "unit": "kg",
        "category": "produce",
        "country": "CO",
    }
    assert auth_client.post("/inventory/products", json=payload).status_code == 201
    assert auth_client.post("/inventory/products", json=payload).status_code == 400


def test_inbound_order_requires_auth(anon_client: TestClient):
    resp = anon_client.post(
        "/inventory/orders/inbound",
        json={
            "ingredient_id": 1,
            "quantity": 1,
            "supplier_name": "Test Supplier",
            "location_id": 1,
        },
    )
    assert resp.status_code == 401


def test_inbound_increases_stock(auth_client: TestClient):
    sku = _unique_sku()
    product = auth_client.post(
        "/inventory/products",
        json={
            "name": "Inbound test",
            "sku": sku,
            "unit": "kg",
            "category": "meat",
            "country": "CO",
        },
    ).json()

    inbound = auth_client.post(
        "/inventory/orders/inbound",
        json={
            "ingredient_id": product["id"],
            "quantity": 15,
            "supplier_name": "Carnes del Valle S.A.",
            "location_id": 3,
        },
    )
    assert inbound.status_code == 201
    assert inbound.json()["user_uuid"]

    refreshed = auth_client.get(f"/inventory/products/{product['id']}").json()
    assert refreshed["current_stock"] == 15.0


def test_outbound_insufficient_stock_rejected(auth_client: TestClient):
    sku = _unique_sku()
    product = auth_client.post(
        "/inventory/products",
        json={
            "name": "Outbound guard",
            "sku": sku,
            "unit": "kg",
            "category": "meat",
            "country": "US",
        },
    ).json()

    resp = auth_client.post(
        "/inventory/orders/outbound",
        json={
            "ingredient_id": product["id"],
            "quantity": 5,
            "reason": "consumption",
            "location_id": 1,
        },
    )
    assert resp.status_code == 400
    assert "Insufficient stock for ingredient" in resp.json()["detail"]
    assert "Available: 0.0" in resp.json()["detail"]
    assert "requested: 5.0" in resp.json()["detail"]


def test_outbound_waste_reduces_stock(auth_client: TestClient):
    sku = _unique_sku()
    product = auth_client.post(
        "/inventory/products",
        json={
            "name": "Waste test",
            "sku": sku,
            "unit": "litre",
            "category": "sauce",
            "country": "CO",
        },
    ).json()
    auth_client.post(
        "/inventory/orders/inbound",
        json={
            "ingredient_id": product["id"],
            "quantity": 10,
            "supplier_name": "Salsas Artesanales Ltda.",
            "location_id": 2,
        },
    )
    outbound = auth_client.post(
        "/inventory/orders/outbound",
        json={
            "ingredient_id": product["id"],
            "quantity": 3,
            "reason": "waste",
            "location_id": 2,
        },
    )
    assert outbound.status_code == 201
    assert outbound.json()["reason"] == "waste"
    assert (
        auth_client.get(f"/inventory/products/{product['id']}").json()["current_stock"]
        == 7.0
    )


def test_outbound_invalid_reason_rejected(auth_client: TestClient):
    sku = _unique_sku()
    product = auth_client.post(
        "/inventory/products",
        json={
            "name": "Reason validation",
            "sku": sku,
            "unit": "kg",
            "category": "produce",
            "country": "CO",
        },
    ).json()
    resp = auth_client.post(
        "/inventory/orders/outbound",
        json={
            "ingredient_id": product["id"],
            "quantity": 1,
            "reason": "spoiled",
            "location_id": 1,
        },
    )
    assert resp.status_code == 422


def test_list_orders_includes_inbound_and_outbound(anon_client: TestClient):
    resp = anon_client.get("/inventory/orders")
    assert resp.status_code == 200
    body = resp.json()
    assert "inbound" in body and "outbound" in body
    assert len(body["inbound"]) >= 4
    assert len(body["outbound"]) >= 3
    assert body["inbound"][0]["ingredient_sku"]
