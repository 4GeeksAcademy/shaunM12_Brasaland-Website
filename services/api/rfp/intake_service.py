"""Orchestrate RFP intake graph execution and Postgres persistence."""

from __future__ import annotations

import logging
import shutil
import threading
from hashlib import sha256
from pathlib import Path

from sqlmodel import Session

from database import get_engine

from rfp.constants import (
    RFP_INTAKE_PDF_DIR,
    RFP_SEED_ASSETS_DIR,
    STATUS_ANALYZING,
    STATUS_DISCARDED,
    STATUS_FAILED,
    STATUS_INTAKE_COMPLETE,
)
from data.pipelines.rfp_intake_graph import invoke_rfp_intake
from rfp.repository import (
    append_trace_event,
    create_ticket_analyzing,
    get_ticket,
    get_ticket_or_raise,
    update_ticket,
    upsert_department_section,
)

logger = logging.getLogger(__name__)

_intake_lock = threading.Lock()
_intake_running: set[str] = set()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ticket_pdf_dir(ticket_id: str) -> Path:
    directory = RFP_INTAKE_PDF_DIR / ticket_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_final_proposal_mirror(ticket_id: str, markdown: str) -> str:
    """Write merged proposal beside source PDF (gitignored intake dir)."""
    path = ticket_pdf_dir(ticket_id) / "final_proposal.md"
    path.write_text(markdown, encoding="utf-8")
    return f"data/raw/intakes/{ticket_id}/final_proposal.md"


def delete_ticket_files(ticket_id: str) -> None:
    """Remove stored PDF directory for a ticket (best-effort after DB delete)."""
    import shutil

    directory = RFP_INTAKE_PDF_DIR / ticket_id
    if directory.exists():
        shutil.rmtree(directory)


def store_uploaded_pdf(ticket_id: str, source: Path) -> tuple[str, str]:
    """Copy PDF to data/raw/intakes/{ticket_id}/source.pdf; return relative path + hash."""
    dest = ticket_pdf_dir(ticket_id) / "source.pdf"
    shutil.copy2(source, dest)
    rel_path = f"data/raw/intakes/{ticket_id}/source.pdf"
    return rel_path, _sha256_file(dest)


def resolve_pdf_path(relative_or_absolute: str) -> Path:
    path = Path(relative_or_absolute)
    if path.is_file():
        return path.resolve()
    from data.pipelines.rfp_intake import repo_root

    candidate = repo_root() / relative_or_absolute
    return candidate.resolve()


def ensure_ticket_markdown(session: Session, ticket_id: str) -> str:
    """Return ticket markdown, re-converting the source PDF when stored text is too short."""
    from data.pipelines.rfp_intake import convert_pdf_to_markdown

    from rfp.constants import MIN_RFP_MARKDOWN_CHARS

    ticket = get_ticket_or_raise(session, ticket_id)
    markdown = (ticket.markdown_text or "").strip()
    if len(markdown) >= MIN_RFP_MARKDOWN_CHARS:
        return markdown
    if not ticket.source_pdf_path:
        return markdown

    try:
        refreshed = convert_pdf_to_markdown(resolve_pdf_path(ticket.source_pdf_path)).strip()
    except Exception:
        logger.warning(
            "Could not refresh short markdown for ticket %s",
            ticket_id,
            exc_info=True,
        )
        return markdown

    if len(refreshed) > len(markdown):
        update_ticket(session, ticket_id, markdown_text=refreshed)
        logger.info(
            "Refreshed markdown for ticket %s (%d → %d chars)",
            ticket_id,
            len(markdown),
            len(refreshed),
        )
        return refreshed
    return markdown


def persist_graph_state(session: Session, ticket_id: str, state: dict) -> None:
    """Write graph terminal state, sections, and trace events to Postgres."""
    status = state.get("status") or STATUS_FAILED
    metadata = dict(state.get("metadata") or {})
    if "readability_scores" in state:
        metadata["readability_scores"] = state["readability_scores"]

    update_fields: dict = {
        "status": status,
        "metadata": metadata,
        "departments_needed": list(state.get("departments_needed") or []),
        "unmapped_topics": list(state.get("unmapped_topics") or []),
        "conflicts": list(state.get("conflicts") or []),
        "intake_summary": state.get("intake_summary"),
        "requires_ceo_approval": bool(state.get("requires_ceo_approval")),
        "markdown_text": state.get("markdown_text"),
        "discard_reason": state.get("discard_reason"),
        "error_message": state.get("error_message"),
        "error_code": state.get("error_code"),
    }
    update_ticket(session, ticket_id, **update_fields)

    if status == STATUS_INTAKE_COMPLETE:
        for dept in state.get("departments_needed") or []:
            upsert_department_section(
                session,
                ticket_id=ticket_id,
                department_id=dept,
                key_aspects=list((state.get("department_key_aspects") or {}).get(dept) or []),
            )

    for event in state.get("trace_events") or []:
        node = str(event.get("node") or "unknown")
        append_trace_event(session, ticket_id=ticket_id, node=node, payload=dict(event))


def run_intake_for_ticket(session: Session, ticket_id: str) -> None:
    """Load ticket PDF, invoke graph, persist results."""
    ticket = get_ticket_or_raise(session, ticket_id)
    if not ticket.source_pdf_path:
        update_ticket(
            session,
            ticket_id,
            status=STATUS_FAILED,
            error_code="storage_error",
            error_message="Missing source PDF path on ticket.",
        )
        return

    pdf_path = resolve_pdf_path(ticket.source_pdf_path)
    state = invoke_rfp_intake(ticket_id=ticket_id, pdf_path=pdf_path)
    persist_graph_state(session, ticket_id, state)
    ensure_ticket_markdown(session, ticket_id)


def run_intake_background_task(ticket_id: str) -> None:
    """BackgroundTasks entrypoint — guard against duplicate concurrent runs."""
    with _intake_lock:
        if ticket_id in _intake_running:
            logger.info("Skipping duplicate intake run for ticket %s", ticket_id)
            return
        _intake_running.add(ticket_id)
    try:
        with Session(get_engine()) as session:
            ticket = get_ticket(session, ticket_id)
            if ticket is None or ticket.status != STATUS_ANALYZING:
                return
            run_intake_for_ticket(session, ticket_id)
    except Exception:  # noqa: BLE001 — persist failed status, never crash worker
        logger.exception("RFP intake background task failed for %s", ticket_id)
        try:
            with Session(get_engine()) as session:
                update_ticket(
                    session,
                    ticket_id,
                    status=STATUS_FAILED,
                    error_code="pipeline_error",
                    error_message="RFP intake failed unexpectedly.",
                )
        except Exception:
            logger.exception("Could not persist failed status for %s", ticket_id)
    finally:
        with _intake_lock:
            _intake_running.discard(ticket_id)


def create_ticket_from_pdf(session: Session, source_pdf: Path) -> str:
    """Create analyzing ticket, store PDF, run intake — convenience for tests/seeds."""
    ticket = create_ticket_analyzing(session)
    rel_path, pdf_hash = store_uploaded_pdf(ticket.ticket_id, source_pdf)
    update_ticket(
        session,
        ticket.ticket_id,
        source_pdf_path=rel_path,
        source_pdf_sha256=pdf_hash,
        status=STATUS_ANALYZING,
    )
    run_intake_for_ticket(session, ticket.ticket_id)
    return ticket.ticket_id


def seed_asset_path(filename: str) -> Path:
    path = RFP_SEED_ASSETS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Seed PDF not found: {path}")
    return path


__all__ = [
    "create_ticket_from_pdf",
    "delete_ticket_files",
    "ensure_ticket_markdown",
    "persist_graph_state",
    "resolve_pdf_path",
    "run_intake_background_task",
    "run_intake_for_ticket",
    "seed_asset_path",
    "store_uploaded_pdf",
    "ticket_pdf_dir",
]
