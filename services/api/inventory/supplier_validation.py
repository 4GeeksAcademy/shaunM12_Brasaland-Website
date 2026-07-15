"""Resolve and validate supplier directory references for inbound orders."""

from __future__ import annotations

from suppliers import repository as suppliers_repository
from suppliers.models import SupplierResponse

from .constants import country_for_location
from .schemas import InboundOrderCreate

INVENTORY_TO_SUPPLIER_CATEGORY: dict[str, str] = {
    "meat": "meat",
    "seafood": "meat",
    "produce": "vegetables_and_greens",
    "sauce": "sauces_and_seasonings",
    "beverage": "beverages",
    "packaging": "packaging",
    "cleaning": "cleaning_products",
}

LOCATION_TO_SUPPLIER_COUNTRY = {
    "CO": "Colombia",
    "US": "USA",
}

# Demo / legacy inbound labels → canonical supplier directory names.
SUPPLIER_NAME_ALIASES: dict[str, str] = {
    "Carnes del Valle S.A.": "Carnes del Valle S.A.S.",
    "MiamiMeat Co.": "Miami Meat Distributors LLC",
    "Salsas Artesanales Ltda.": "Condimentos El Sabor",
    "Pacífico Seafood S.A.": "Frigorífico Antioqueño",
    "Florida Gulf Seafood Co.": "Miami Meat Distributors LLC",
    "Empaques Andinos Ltda.": "Empaques y Más",
    "Frutas del Campo Ltda.": "Verduras La Cosecha",
    "Sunrise Produce Co.": "Sunshine Produce FL",
    "Gulf Coast Flavors Inc.": "Latin Flavors Inc.",
    "Florida Beverage Supply": "Latin Flavors Inc.",
    "Bebidas Andinas S.A.": "Distribuidora RefriCol",
    "US Prime Meats LLC": "Miami Meat Distributors LLC",
}


class SupplierNotFoundError(ValueError):
    """Raised when ``supplier_id`` or legacy name does not match the directory."""


class SupplierInactiveError(ValueError):
    """Raised when the supplier exists but is suspended."""


class SupplierCountryMismatchError(ValueError):
    """Raised when supplier country does not match the receiving location."""


def supplier_country_for_location(location_id: int) -> str:
    return LOCATION_TO_SUPPLIER_COUNTRY[country_for_location(location_id)]


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _supplier_matches_name(supplier: SupplierResponse, raw_name: str) -> bool:
    canonical = SUPPLIER_NAME_ALIASES.get(raw_name, raw_name)
    return _normalize_name(supplier.name) == _normalize_name(canonical) or (
        _normalize_name(canonical) in _normalize_name(supplier.name)
    )


def find_supplier_id_by_name(name: str, location_id: int) -> SupplierResponse | None:
    """Best-effort lookup for seed data and legacy inbound payloads."""
    country = supplier_country_for_location(location_id)
    for supplier in suppliers_repository.list_suppliers(country=country):
        if _supplier_matches_name(supplier, name):
            return supplier
    return None


def _validate_supplier_record(
    supplier: SupplierResponse,
    location_id: int,
    ingredient_category: str | None = None,
) -> None:
    expected_country = supplier_country_for_location(location_id)
    if supplier.country != expected_country:
        raise SupplierCountryMismatchError(
            f"Supplier '{supplier.name}' operates in {supplier.country}, "
            f"but location {location_id} requires {expected_country}."
        )
    if supplier.status != "active":
        raise SupplierInactiveError(
            f"Supplier '{supplier.name}' is {supplier.status} and cannot receive orders."
        )
    if ingredient_category is not None:
        mapped = INVENTORY_TO_SUPPLIER_CATEGORY.get(ingredient_category)
        if mapped is not None and mapped not in supplier.categories:
            raise SupplierNotFoundError(
                f"Supplier '{supplier.name}' does not supply category '{ingredient_category}'."
            )


def resolve_inbound_supplier(
    payload: InboundOrderCreate,
    *,
    ingredient_category: str | None = None,
) -> tuple[int, str]:
    """Return validated ``(supplier_id, supplier_name_snapshot)`` for a SupplyOrder."""
    supplier: SupplierResponse | None = None

    if payload.supplier_id is not None:
        supplier = suppliers_repository.get_supplier(payload.supplier_id)

    if supplier is None and payload.supplier_name:
        supplier = find_supplier_id_by_name(payload.supplier_name, payload.location_id)

    if supplier is None:
        raise SupplierNotFoundError("Supplier not found in directory.")

    _validate_supplier_record(
        supplier,
        payload.location_id,
        ingredient_category=ingredient_category,
    )
    return supplier.id, supplier.name
