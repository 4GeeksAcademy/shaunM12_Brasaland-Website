"""Shared validation and normalization helpers for incident manager workflows."""

from __future__ import annotations

from datetime import datetime

LEGACY_CATEGORY_MAP: dict[str, str] = {
    "equipment": "equipment_failure",
    "equipment failure": "equipment_failure",
    "supply": "supply_issue",
    "supply issue": "supply_issue",
    "customer complaint": "customer_complaint",
    "food_quality": "customer_complaint",
    "staff": "staff_issue",
    "staff issue": "staff_issue",
    "facility issue": "facility_issue",
    "pos system": "pos_system",
    "delivery issue": "delivery_issue",
}

LEGACY_STATUS_MAP: dict[str, str] = {
    "open": "open",
    "in progress": "in_progress",
    "resolved": "resolved",
    "discarded": "discarded",
    "closed": "resolved",
}

LEGACY_LOCATION_TO_BRANCH: dict[str, str] = {
    "COL-01": "medellin_centro",
    "COL-02": "medellin_laureles",
    "COL-03": "medellin_envigado",
    "COL-04": "medellin_bello",
    "COL-05": "medellin_itagui",
    "COL-06": "bogota_chapinero",
    "COL-07": "bogota_usaquen",
    "COL-08": "cali_granada",
    "COL-09": "barranquilla_norte",
    "COL-10": "central",
    "FLA-01": "miami_doral",
    "FLA-02": "miami_hialeah",
    "FLA-03": "miami_kendall",
    "FLA-04": "orlando_international",
}

# Original analyzer CSV category codes (pre-transform).
ANALYZER_CATEGORY_CODES: tuple[str, ...] = (
    "CUSTOMER_COMPLAINT",
    "EQUIPMENT",
    "SUPPLY",
    "FOOD_QUALITY",
    "STAFF",
)


def validate_enum_value(value: str, allowed: tuple[str, ...], message: str) -> str:
    cleaned = value.strip()
    if cleaned not in allowed:
        raise ValueError(message)
    return cleaned


def normalize_legacy_category(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower().replace("-", "_")
    if not cleaned:
        return None
    return LEGACY_CATEGORY_MAP.get(cleaned, cleaned)


def normalize_legacy_status(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower().replace("-", " ")
    if not cleaned:
        return None
    return LEGACY_STATUS_MAP.get(cleaned, cleaned.replace(" ", "_"))


def normalize_legacy_branch(location_id: str | None) -> str | None:
    if location_id is None:
        return None
    cleaned = location_id.strip().upper()
    if not cleaned:
        return None
    return LEGACY_LOCATION_TO_BRANCH.get(cleaned)


def parse_legacy_date(value: str | None) -> datetime | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return datetime.strptime(cleaned, "%Y-%m-%d")
