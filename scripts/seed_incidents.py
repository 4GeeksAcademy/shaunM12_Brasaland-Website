#!/usr/bin/env python3
"""Load historical incident CSV rows into centralized incident manager tables."""

from __future__ import annotations

import csv
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

API_ROOT = REPO_ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

def _load_local_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module '{module_name}' from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Force-load local API modules (avoid same-name packages from site-packages).
for _module_name in ("config", "database"):
    sys.modules.pop(_module_name, None)

_load_local_module("config", API_ROOT / "config.py")
database = _load_local_module("database", API_ROOT / "database.py")

from incidents import repository  # noqa: E402
from incidents.schemas import IncidentCreate  # noqa: E402
from packages.shared.incidents_validation import (  # noqa: E402
    normalize_legacy_branch,
    normalize_legacy_category,
    normalize_legacy_status,
    parse_legacy_date,
)

get_engine = database.get_engine


@dataclass
class SeedStats:
    inserted: int = 0
    skipped_duplicates: int = 0
    invalid: int = 0


def _csv_path() -> Path:
    return REPO_ROOT / "data" / "incidents-brasaland.csv"


def _source_key(row: dict[str, str], row_number: int) -> str:
    incident_id = (row.get("incident_id") or "").strip()
    if incident_id:
        return f"legacy_incident:{incident_id}"
    return f"legacy_row:{row_number}"


def _build_payload(row: dict[str, str]) -> IncidentCreate:
    title_source = (row.get("category") or "incident").strip()
    title = f"Historical Incident - {title_source}"
    description = (row.get("description") or "").strip()
    if not description:
        raise ValueError("description is required")

    category = normalize_legacy_category(row.get("category"))
    if not category:
        raise ValueError("category is required")

    status = normalize_legacy_status(row.get("status")) or "open"
    branch = normalize_legacy_branch(row.get("location_id"))
    if not branch:
        raise ValueError("location_id does not map to a supported branch")

    created_at = parse_legacy_date(row.get("date"))

    # Historical import policy: every CSV row is treated as customer-origin.
    return IncidentCreate(
        title=title,
        description=description,
        category=category,
        status=status,
        origin="customer",
        branch=branch,
        created_at=created_at,
    )


def seed_incidents() -> SeedStats:
    csv_path = _csv_path()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    stats = SeedStats()

    with csv_path.open("r", encoding="utf-8", newline="") as handle, Session(get_engine()) as session:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            source_key = _source_key(row, row_number)
            if repository.has_seed_key(session, source_key):
                stats.skipped_duplicates += 1
                continue

            try:
                payload = _build_payload(row)
                repository.create_seeded_incident(session, payload, source_key=source_key)
                stats.inserted += 1
            except Exception as exc:
                stats.invalid += 1
                print(f"[seed-incidents] row {row_number} skipped: {exc}", file=sys.stderr)

    return stats


def main() -> int:
    try:
        stats = seed_incidents()
    except Exception as exc:
        print(f"[seed-incidents] failed: {exc}", file=sys.stderr)
        return 1

    print(
        "[seed-incidents] done: "
        f"inserted={stats.inserted}, "
        f"skipped_duplicates={stats.skipped_duplicates}, "
        f"invalid={stats.invalid}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
