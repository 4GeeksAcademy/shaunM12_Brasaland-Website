#!/usr/bin/env python3
"""Load historical incident CSV rows into centralized incident manager tables."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session

from database import get_engine
from incidents import repository
from incidents.schemas import IncidentCreate


def _ensure_repo_root_on_path() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current.parent, *current.parents):
        if (candidate / "packages" / "shared" / "incidents_validation.py").exists():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return candidate
    if Path("/app/packages/shared/incidents_validation.py").exists():
        if "/app" not in sys.path:
            sys.path.insert(0, "/app")
        return Path("/app")
    return current.parents[3]


_REPO_ROOT = _ensure_repo_root_on_path()

from packages.shared.incidents_validation import (  # noqa: E402
    ANALYZER_CATEGORY_CODES,
    normalize_legacy_branch,
    normalize_legacy_category,
    normalize_legacy_status,
    parse_legacy_date,
)


@dataclass
class SeedStats:
    inserted: int = 0
    skipped_duplicates: int = 0
    invalid: int = 0


def _csv_path() -> Path:
    return _REPO_ROOT / "data" / "incidents-brasaland.csv"


def _source_key(row: dict[str, str], row_number: int) -> str:
    incident_id = (row.get("incident_id") or "").strip()
    if incident_id:
        return f"legacy_incident:{incident_id}"
    return f"legacy_row:{row_number}"


def _assert_analyzer_valid(row: dict[str, str]) -> None:
    """Skip the same invalid set used by the incident file analyzer (CONTEXT)."""
    location_id = (row.get("location_id") or "").strip()
    if not location_id or normalize_legacy_branch(location_id) is None:
        raise ValueError("missing or invalid location_id")

    category = (row.get("category") or "").strip().upper()
    if category not in ANALYZER_CATEGORY_CODES:
        raise ValueError("missing or invalid category")

    description = (row.get("description") or "").strip()
    if len(description) < 5:
        raise ValueError("empty or too-short description")

    status = (row.get("status") or "").strip().upper()
    score_raw = (row.get("satisfaction_score") or "").strip()
    if status == "CLOSED" and not score_raw:
        raise ValueError("closed case without satisfaction_score")
    if score_raw:
        try:
            score = int(score_raw)
        except ValueError as exc:
            raise ValueError("satisfaction_score out of range") from exc
        if score < 1 or score > 5:
            raise ValueError("satisfaction_score out of range")


def _build_payload(row: dict[str, str]) -> IncidentCreate:
    _assert_analyzer_valid(row)

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
        category=category,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        origin="customer",
        branch=branch,  # type: ignore[arg-type]
        created_at=created_at,
    )


def seed_incidents() -> SeedStats:
    csv_path = _csv_path()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    stats = SeedStats()

    with csv_path.open("r", encoding="utf-8", newline="") as handle, Session(
        get_engine()
    ) as session:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            source_key = _source_key(row, row_number)
            if repository.has_seed_key(session, source_key):
                stats.skipped_duplicates += 1
                continue

            try:
                payload = _build_payload(row)
                repository.create_seeded_incident(
                    session, payload, source_key=source_key
                )
                stats.inserted += 1
            except Exception as exc:  # noqa: BLE001 — report and continue
                stats.invalid += 1
                print(
                    f"[seed-incidents] row {row_number} skipped: {exc}",
                    file=sys.stderr,
                )

    return stats


def main() -> int:
    try:
        stats = seed_incidents()
    except Exception as exc:  # noqa: BLE001
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
