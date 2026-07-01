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

VALID_EXIT_REASONS = ["consumption", "waste"]

MIN_LOCATION_ID = 1
MAX_LOCATION_ID = 14


def country_for_location(location_id: int) -> str:
    """Colombia branches 1-9; US branches 10-14."""
    if not MIN_LOCATION_ID <= location_id <= MAX_LOCATION_ID:
        raise ValueError(
            f"location_id must be between {MIN_LOCATION_ID} and {MAX_LOCATION_ID}"
        )
    return "CO" if location_id <= 9 else "US"
