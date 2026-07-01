"""Canonical incident-domain constants for Brasaland."""

from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Iterable

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from packages.shared.incidents_validation import LEGACY_CATEGORY_MAP, LEGACY_STATUS_MAP

BRANCH_VALUES: tuple[str, ...] = (
    "central",
    "medellin_centro",
    "medellin_laureles",
    "medellin_envigado",
    "medellin_bello",
    "medellin_itagui",
    "bogota_chapinero",
    "bogota_usaquen",
    "cali_granada",
    "barranquilla_norte",
    "miami_doral",
    "miami_hialeah",
    "miami_kendall",
    "orlando_international",
    "fort_lauderdale",
)

BRANCH_LABELS: dict[str, str] = {
    "central": "Central (Medellin / Miami)",
    "medellin_centro": "Medellin Centro",
    "medellin_laureles": "Medellin Laureles",
    "medellin_envigado": "Medellin Envigado",
    "medellin_bello": "Medellin Bello",
    "medellin_itagui": "Medellin Itagui",
    "bogota_chapinero": "Bogota Chapinero",
    "bogota_usaquen": "Bogota Usaquen",
    "cali_granada": "Cali Granada",
    "barranquilla_norte": "Barranquilla Norte",
    "miami_doral": "Miami Doral",
    "miami_hialeah": "Miami Hialeah",
    "miami_kendall": "Miami Kendall",
    "orlando_international": "Orlando International Drive",
    "fort_lauderdale": "Fort Lauderdale",
}

CATEGORY_VALUES: tuple[str, ...] = (
    "equipment_failure",
    "supply_issue",
    "customer_complaint",
    "staff_issue",
    "facility_issue",
    "pos_system",
    "delivery_issue",
    "other",
)

STATUS_VALUES: tuple[str, ...] = (
    "open",
    "in_progress",
    "resolved",
    "discarded",
)

ORIGIN_VALUES: tuple[str, ...] = (
    "customer",
    "branch",
    "internal",
)

STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "open": ("in_progress", "discarded"),
    "in_progress": ("resolved", "discarded"),
    "resolved": (),
    "discarded": (),
}

def is_allowed(value: str, allowed: Iterable[str]) -> bool:
    return value in set(allowed)

