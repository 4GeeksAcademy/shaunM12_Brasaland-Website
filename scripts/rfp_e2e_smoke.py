#!/usr/bin/env python3
"""RFP full workflow smoke — P1 intake → P2 draft → P3 approval → completed (context-27 P3 Phase 5).

Mirrors ``test_rfp_e2e.py`` without HTTP. Uses mocked generation by default for a
fast, deterministic run (same draft text as unit/E2E tests).

Usage::

    cd services/api && uv run python ../../scripts/rfp_e2e_smoke.py --seed 2
    cd services/api && uv run python ../../scripts/rfp_e2e_smoke.py --seed 1

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
from rfp.approval_service import (  # noqa: E402
    get_final_document,
    run_approval_for_ticket,
    submit_ceo_decision,
    submit_department_decision,
)
from rfp.constants import (  # noqa: E402
    APPROVAL_DECISION_APPROVE,
    APPROVAL_STATUS_AWAITING_HUMAN,
    CEO_DECISION_APPROVE,
    SEED_PDF_FILES,
    STATUS_AWAITING_CEO_APPROVAL,
    STATUS_AWAITING_DEPARTMENT_APPROVAL,
    STATUS_COMPLETED,
    STATUS_WAITING_FOR_APPROVAL,
)
from rfp.draft_service import run_generation_for_ticket  # noqa: E402
from rfp.graph import reset_graph_cache  # noqa: E402
from rfp.intake_service import create_ticket_from_pdf, seed_asset_path  # noqa: E402
from rfp.models import ensure_rfp_schema  # noqa: E402
from rfp.repository import ticket_detail  # noqa: E402

logger = logging.getLogger(__name__)

SEED_CHOICES = {"1": 0, "2": 1}

MOCK_COMPLIANT_DRAFT = """
Brasaland department proposal section for this RFP response.

Brand co-marketing and exclusivity terms are included in this proposal presentation.
Operational feasibility and staffing plan covers peak season operations with a clear
setup timeline and service cadence for weekly delivery.
Pricing and volume-based ingredient costs are quoted at $45,000 USD per year
(COP 180,000,000 at 1 USD = 4000 COP). Supplier lead times for contract volume
are 12 business days from contract signature.
New recipe or standard development time includes certification and rollout across
locations for training and quality standards.

We deliver consistent product quality, warm customer experience, and speed of
service without sacrificing quality. This offer is valid for 30 days from issuance.
"""


def _require_env() -> None:
    if not config.DATABASE_URL:
        raise SystemExit("DATABASE_URL is required for RFP E2E smoke runs.")
    if not config.GENERATION_BASE_URL or not config.GENERATION_API_KEY:
        raise SystemExit("GENERATION_BASE_URL and GENERATION_API_KEY are required.")


def _install_generation_mock() -> None:
    from data.pipelines import rfp_generation as gen

    gen._generation_available = lambda: True  # noqa: SLF001

    def _fake_chat_json(system: str, user: str) -> dict:
        if "missing_topics" in system:
            return {"missing_topics": []}
        return {}

    def _fake_chat_text(system: str, user: str) -> str:
        return MOCK_COMPLIANT_DRAFT

    gen._chat_json = _fake_chat_json  # noqa: SLF001
    gen._chat_text = _fake_chat_text  # noqa: SLF001


def _print_stage(label: str, detail) -> None:
    print(f"\n--- {label} ---")
    print(
        json.dumps(
            {
                "ticket_id": detail.ticket_id,
                "status": detail.status,
                "status_label": detail.status_label,
                "requires_ceo_approval": detail.requires_ceo_approval,
                "departments": [s.department_id for s in detail.sections],
                "section_count": len(detail.sections),
            },
            indent=2,
        )
    )


def run_e2e(seed_index: int, *, approver: str) -> str:
    reset_graph_cache()

    with Session(get_engine()) as session:
        ensure_rfp_schema(session)

        ticket_id = create_ticket_from_pdf(
            session,
            seed_asset_path(SEED_PDF_FILES[seed_index]),
        )
        _print_stage("P1 intake", ticket_detail(session, ticket_id))

        run_generation_for_ticket(session, ticket_id)
        detail = ticket_detail(session, ticket_id)
        if detail.status != STATUS_WAITING_FOR_APPROVAL:
            raise SystemExit(f"P2 failed — expected waiting_for_approval, got {detail.status}")
        _print_stage("P2 generation", detail)

        run_approval_for_ticket(session, ticket_id)
        detail = ticket_detail(session, ticket_id)
        if detail.status != STATUS_AWAITING_DEPARTMENT_APPROVAL:
            raise SystemExit(
                f"P3 start failed — expected awaiting_department_approval, got {detail.status}"
            )
        _print_stage("P3 approval interrupts", detail)

        for section in detail.sections:
            if section.approval_status != APPROVAL_STATUS_AWAITING_HUMAN:
                continue
            submit_department_decision(
                session,
                ticket_id=ticket_id,
                department_id=section.department_id,
                decision=APPROVAL_DECISION_APPROVE,
                approver=approver,
            )
            logger.info("Approved department %s", section.department_id)

        detail = ticket_detail(session, ticket_id)
        if detail.requires_ceo_approval:
            if detail.status != STATUS_AWAITING_CEO_APPROVAL:
                raise SystemExit(
                    f"Expected awaiting_ceo_approval after dept approvals, got {detail.status}"
                )
            _print_stage("P3 CEO gate", detail)
            submit_ceo_decision(
                session,
                ticket_id=ticket_id,
                decision=CEO_DECISION_APPROVE,
                approver="Mariana Restrepo",
            )

        detail = ticket_detail(session, ticket_id)
        if detail.status != STATUS_COMPLETED:
            raise SystemExit(f"E2E failed — expected completed, got {detail.status}")
        if not detail.has_final_document:
            raise SystemExit("E2E failed — no final document on completed ticket.")

        final_doc = get_final_document(session, ticket_id)
        _print_stage("Completed", detail)
        print(
            json.dumps(
                {
                    "final_document_length": detail.final_document_length,
                    "generated_at": str(final_doc["generated_at"]),
                    "final_preview": final_doc["final_document_markdown"][:400].strip() + "…",
                },
                indent=2,
            )
        )
        return ticket_id


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="RFP full E2E smoke (intake → draft → approval → completed)."
    )
    parser.add_argument(
        "--seed",
        choices=sorted(SEED_CHOICES),
        default="2",
        help="Seed PDF: 1=Sunset Bay (CEO path), 2=Andes Tech (fast path).",
    )
    parser.add_argument(
        "--approver",
        default="Smoke CLI",
        help="Display name recorded on department approvals.",
    )
    parser.add_argument(
        "--no-mock-generation",
        action="store_true",
        help="Use live LLM for P2 (slow; default is mocked generation).",
    )
    args = parser.parse_args()

    _require_env()
    if not args.no_mock_generation:
        _install_generation_mock()

    seed_index = SEED_CHOICES[args.seed]
    ticket_id = run_e2e(seed_index, approver=args.approver)
    print(f"\nE2E smoke OK — ticket_id={ticket_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
