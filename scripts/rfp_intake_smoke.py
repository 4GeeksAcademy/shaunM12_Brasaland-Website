#!/usr/bin/env python3
"""RFP intake smoke / reprocess CLI — independent of the FastAPI HTTP server (context-27 P1).

Runs the same pipeline entrypoint as ``POST /rfp/tickets`` but from the shell.

Usage::

    cd services/api && uv run python ../../scripts/rfp_intake_smoke.py --seed 1
    cd services/api && uv run python ../../scripts/rfp_intake_smoke.py --pdf path/to/rfp.pdf
    cd services/api && uv run python ../../scripts/rfp_intake_smoke.py --reprocess TICKET_UUID

Requires ``DATABASE_URL`` and ``GENERATION_*`` (same as the API).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "services" / "api"

for _path in (str(API_ROOT), str(REPO_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from sqlmodel import Session  # noqa: E402

import config  # noqa: E402
from database import get_engine  # noqa: E402
from rfp.constants import SEED_PDF_FILES, STATUS_ANALYZING  # noqa: E402
from rfp.intake_service import (  # noqa: E402
    create_ticket_from_pdf,
    run_intake_for_ticket,
    seed_asset_path,
)
from rfp.models import ensure_rfp_schema  # noqa: E402
from rfp.repository import ticket_detail, update_ticket  # noqa: E402

logger = logging.getLogger(__name__)

SEED_CHOICES = {"1": 0, "2": 1, "3": 2}


def _require_env() -> None:
    if not config.DATABASE_URL:
        raise SystemExit("DATABASE_URL is required for RFP intake smoke runs.")
    if not config.GENERATION_BASE_URL or not config.GENERATION_API_KEY:
        raise SystemExit("GENERATION_BASE_URL and GENERATION_API_KEY are required.")


def _print_detail(detail) -> None:
    payload = {
        "ticket_id": detail.ticket_id,
        "status": detail.status,
        "status_label": detail.status_label,
        "requires_ceo_approval": detail.requires_ceo_approval,
        "departments_needed": detail.departments_needed,
        "section_count": len(detail.sections),
        "discard_reason": detail.discard_reason,
        "error_code": detail.error_code,
        "error_message": detail.error_message,
    }
    print(json.dumps(payload, indent=2))


def run_smoke_pdf(pdf_path: Path) -> str:
    with Session(get_engine()) as session:
        ensure_rfp_schema(session)
        ticket_id = create_ticket_from_pdf(session, pdf_path)
        detail = ticket_detail(session, ticket_id)
        _print_detail(detail)
        return ticket_id


def run_reprocess(ticket_id: str) -> None:
    with Session(get_engine()) as session:
        ensure_rfp_schema(session)
        update_ticket(session, ticket_id, status=STATUS_ANALYZING)
        run_intake_for_ticket(session, ticket_id)
        detail = ticket_detail(session, ticket_id)
        _print_detail(detail)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="RFP intake smoke / reprocess (no HTTP).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--seed",
        choices=sorted(SEED_CHOICES),
        help="Process a committed milestone-9 seed PDF (1=Sunset Bay, 2=Andes Tech, 3=franchise).",
    )
    group.add_argument("--pdf", type=Path, help="Path to a local PDF file.")
    group.add_argument(
        "--reprocess",
        metavar="TICKET_ID",
        help="Re-run intake for an existing ticket (resets status to analyzing).",
    )
    args = parser.parse_args()

    _require_env()

    if args.reprocess:
        run_reprocess(args.reprocess.strip())
        return 0

    if args.seed:
        pdf_path = seed_asset_path(SEED_PDF_FILES[SEED_CHOICES[args.seed]])
    else:
        pdf_path = args.pdf.resolve()
        if not pdf_path.is_file():
            raise SystemExit(f"PDF not found: {pdf_path}")

    run_smoke_pdf(pdf_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
