"""Supplier directory API tests.

The ``client`` fixture (with authentication bypassed) lives in ``conftest.py``.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_seed_loads_fifteen_suppliers(client: TestClient):
    response = client.get("/api/suppliers")
    assert response.status_code == 200
    suppliers = response.json()
    assert len(suppliers) == 15
    assert sum(item["status"] == "suspended" for item in suppliers) == 2


def test_filter_by_country_and_category(client: TestClient):
    usa_meat = client.get("/api/suppliers", params={"country": "USA", "category": "meat"})
    assert usa_meat.status_code == 200
    rows = usa_meat.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Miami Meat Distributors LLC"

    beverages = client.get("/api/suppliers", params={"category": "beverages"})
    assert beverages.status_code == 200
    names = {row["name"] for row in beverages.json()}
    assert "Distribuidora RefriCol" in names
    assert "Latin Flavors Inc." in names
    assert "Bebidas Andinas" in names


def test_create_rejects_invalid_country_currency(client: TestClient):
    response = client.post(
        "/api/suppliers",
        json={
            "name": "Invalid Supplier",
            "country": "Colombia",
            "categories": ["meat"],
            "rate_per_unit": 1000,
            "currency": "USD",
            "status": "active",
        },
    )
    assert response.status_code == 422


def test_rate_patch_updates_timestamp(client: TestClient):
    listing = client.get("/api/suppliers", params={"country": "USA", "category": "packaging"})
    supplier = listing.json()[0]
    original_updated_at = supplier["rate_updated_at"]

    patched = client.patch(
        f"/api/suppliers/{supplier['id']}/rate",
        json={"rate_per_unit": 0.4},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["rate_per_unit"] == 0.4
    assert body["rate_updated_at"] != original_updated_at


def test_status_toggle_and_not_found(client: TestClient):
    supplier = client.get("/api/suppliers").json()[0]
    toggled = client.patch(
        f"/api/suppliers/{supplier['id']}/status",
        json={"status": "suspended" if supplier["status"] == "active" else "active"},
    )
    assert toggled.status_code == 200

    missing = client.get("/api/suppliers/99999")
    assert missing.status_code == 404


def test_notes_patch_and_get_by_id(client: TestClient):
    supplier = client.get("/api/suppliers").json()[0]
    supplier_id = supplier["id"]

    patched = client.patch(
        f"/api/suppliers/{supplier_id}/notes",
        json={"notes": "Updated procurement note for testing."},
    )
    assert patched.status_code == 200
    assert patched.json()["notes"] == "Updated procurement note for testing."

    detail = client.get(f"/api/suppliers/{supplier_id}")
    assert detail.status_code == 200
    assert detail.json()["notes"] == "Updated procurement note for testing."

    cleared = client.patch(f"/api/suppliers/{supplier_id}/notes", json={"notes": ""})
    assert cleared.status_code == 200
    assert cleared.json()["notes"] is None
