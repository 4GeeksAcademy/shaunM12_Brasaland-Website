"""Validation constants for the inventory domain."""

from __future__ import annotations

VALID_CATEGORIES = [
    "meat",
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
