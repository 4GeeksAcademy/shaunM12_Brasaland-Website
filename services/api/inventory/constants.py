"""Validation constants for the inventory domain."""

from __future__ import annotations

VALID_CATEGORIES = [
    "meat",
    "seafood",
    "produce",
    "sauce",
    "beverage",
    "packaging",
    "cleaning",
]

VALID_COUNTRIES = ["CO", "US"]

VALID_EXIT_REASONS = ["kitchen_use", "waste", "spoilage", "theft"]

MIN_LOCATION_ID = 1
MAX_LOCATION_ID = 14

DEFAULT_MIN_STOCK_THRESHOLD = 10.0

CATEGORY_DEFAULT_MIN_STOCK: dict[str, float] = {
    "meat": 25.0,
    "seafood": 15.0,
    "produce": 20.0,
    "sauce": 5.0,
    "beverage": 10.0,
    "packaging": 50.0,
    "cleaning": 5.0,
}


def default_min_stock_for_category(category: str) -> float:
    return CATEGORY_DEFAULT_MIN_STOCK.get(category, DEFAULT_MIN_STOCK_THRESHOLD)


def country_for_location(location_id: int) -> str:
    """Colombia branches 1-9; US branches 10-14."""
    if not MIN_LOCATION_ID <= location_id <= MAX_LOCATION_ID:
        raise ValueError(
            f"location_id must be between {MIN_LOCATION_ID} and {MAX_LOCATION_ID}"
        )
    return "CO" if location_id <= 9 else "US"
