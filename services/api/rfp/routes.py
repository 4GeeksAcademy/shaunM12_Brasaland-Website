"""RFP intake HTTP routes (context-27 Part 1 — Phase 3)."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import config
from auth.dependencies import get_current_user
from database import get_db
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlmodel import Session
from users.models import UserResponse

from .approval_service import (
    ApprovalNotAllowedError,
    DecisionNotAllowedError,
    FinalDocumentNotFoundError,
    NoPendingInterruptError,
    get_final_document,
    regenerate_department_section,
    start_approval_recovery,
    submit_ceo_decision,
    submit_department_decision,
)
from data.pipelines.rfp_approval_packet import ApprovalResponseError
from .constants import (
    ALLOWED_PDF_CONTENT_TYPES,
    APPROVAL_DECISION_VALUES,
    CEO_DECISION_VALUES,
    MAX_UPLOAD_BYTES,
    STATUS_DRAFTING,
    STATUS_FAILED,
    STATUS_INTAKE_COMPLETE,
    STATUS_VALUES,
    status_label,
)
from .draft_service import DraftNotAllowedError, prepare_draft_start, run_draft_background_task
from .intake_service import run_intake_background_task, store_uploaded_pdf
from .repository import (
    RfpSectionNotFoundError,
    RfpTicketNotFoundError,
    create_ticket_analyzing,
    delete_ticket,
    get_ticket_or_raise,
    list_ticket_summaries,
    list_trace_events,
    ticket_detail,
    update_ticket,
)
from .schemas import (
    RfpApprovalStartResponse,
    RfpCeoDecisionRequest,
    RfpCeoDecisionResponse,
    RfpDepartmentDecisionRequest,
    RfpDepartmentDecisionResponse,
    RfpDraftStartResponse,
    RfpFinalDocumentResponse,
    RfpRegenerateResponse,
    RfpTicketCreateResponse,
    RfpTicketDetailResponse,
    RfpTicketSummaryResponse,
    RfpTraceEventResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["rfp"])


def _require_rfp_dependencies() -> None:
    if not config.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RFP intake requires DATABASE_URL.",
        )
    if not (
        config.GENERATION_BASE_URL
        and config.GENERATION_API_KEY
        and config.GENERATION_MODEL_ID
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RFP intake requires GENERATION_BASE_URL, GENERATION_API_KEY, and GENERATION_MODEL_ID.",
        )


def _is_pdf_upload(file: UploadFile) -> bool:
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    return filename.endswith(".pdf") or content_type in ALLOWED_PDF_CONTENT_TYPES


@router.post(
    "/tickets",
    response_model=RfpTicketCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rfp_ticket(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> RfpTicketCreateResponse:
    """Accept a PDF upload and schedule async intake graph execution."""
    _require_rfp_dependencies()

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload must include a PDF file.",
        )
    if not _is_pdf_upload(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload must be a PDF file.",
        )

    payload = await file.read()
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload must include a PDF file.",
        )
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF exceeds the 10 MB upload limit.",
        )

    ticket = create_ticket_analyzing(session)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(payload)
            tmp_path = Path(tmp.name)
        rel_path, pdf_hash = store_uploaded_pdf(ticket.ticket_id, tmp_path)
        update_ticket(
            session,
            ticket.ticket_id,
            source_pdf_path=rel_path,
            source_pdf_sha256=pdf_hash,
        )
    except Exception:
        logger.exception("Failed to store uploaded PDF for ticket %s", ticket.ticket_id)
        update_ticket(
            session,
            ticket.ticket_id,
            status=STATUS_FAILED,
            error_code="storage_error",
            error_message="Could not store uploaded PDF.",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not store uploaded PDF. Please try again.",
        ) from None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    background_tasks.add_task(run_intake_background_task, ticket.ticket_id)
    return RfpTicketCreateResponse(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        created_at=ticket.created_at,
    )


@router.get("/tickets", response_model=list[RfpTicketSummaryResponse])
def list_rfp_tickets(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> list[RfpTicketSummaryResponse]:
    if not config.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RFP intake requires DATABASE_URL.",
        )
    if status_filter is not None and status_filter not in STATUS_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status value.",
        )
    return list_ticket_summaries(
        session, status=status_filter, limit=limit, offset=offset
    )


@router.get("/tickets/{ticket_id}", response_model=RfpTicketDetailResponse)
def get_rfp_ticket(
    ticket_id: str,
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> RfpTicketDetailResponse:
    if not config.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RFP intake requires DATABASE_URL.",
        )
    try:
        return ticket_detail(session, ticket_id)
    except RfpTicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFP ticket not found.",
        ) from exc


@router.delete(
    "/tickets/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_rfp_ticket(
    ticket_id: str,
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> None:
    """Delete one RFP ticket and its sections, trace events, and stored PDF."""
    if not config.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RFP intake requires DATABASE_URL.",
        )
    try:
        delete_ticket(session, ticket_id)
    except RfpTicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFP ticket not found.",
        ) from exc


@router.post(
    "/tickets/{ticket_id}/draft",
    response_model=RfpDraftStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_rfp_draft(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> RfpDraftStartResponse:
    """Start Part 2 draft generation from ``intake_complete`` (async — poll GET)."""
    _require_rfp_dependencies()
    try:
        get_ticket_or_raise(session, ticket_id)
    except RfpTicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFP ticket not found.",
        ) from exc

    try:
        prepare_draft_start(session, ticket_id)
    except DraftNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "status": exc.current_status,
                "status_label": status_label(exc.current_status),
            },
        ) from exc

    background_tasks.add_task(run_draft_background_task, ticket_id)
    return RfpDraftStartResponse(
        ticket_id=ticket_id,
        status=STATUS_DRAFTING,
        status_label=status_label(STATUS_DRAFTING),
    )


@router.post(
    "/tickets/{ticket_id}/approval/start",
    response_model=RfpApprovalStartResponse,
    status_code=status.HTTP_200_OK,
)
def start_rfp_approval(
    ticket_id: str,
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> RfpApprovalStartResponse:
    """Recovery-only idempotent P3 start when auto-start did not run."""
    _require_rfp_dependencies()
    try:
        start_approval_recovery(session, ticket_id)
    except RfpTicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFP ticket not found.",
        ) from exc
    except ApprovalNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "status": exc.current_status,
                "status_label": status_label(exc.current_status),
            },
        ) from exc

    detail = ticket_detail(session, ticket_id)
    return RfpApprovalStartResponse(
        ticket_id=ticket_id,
        status=detail.status,
        status_label=detail.status_label,
    )


@router.post(
    "/tickets/{ticket_id}/sections/{department_id}/decision",
    response_model=RfpDepartmentDecisionResponse,
)
def post_department_decision(
    ticket_id: str,
    department_id: str,
    body: RfpDepartmentDecisionRequest,
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> RfpDepartmentDecisionResponse:
    """Human approve / reject / request_changes for one department section."""
    _require_rfp_dependencies()
    if body.decision not in APPROVAL_DECISION_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision. Expected one of: {sorted(APPROVAL_DECISION_VALUES)}.",
        )

    approver = (current_user.name or current_user.email or "Unknown").strip()
    try:
        result = submit_department_decision(
            session,
            ticket_id=ticket_id,
            department_id=department_id,
            decision=body.decision,
            approver=approver,
            comment=body.comment,
        )
    except RfpTicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFP ticket not found.",
        ) from exc
    except RfpSectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFP department section not found.",
        ) from exc
    except ApprovalResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (DecisionNotAllowedError, NoPendingInterruptError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "status": getattr(exc, "current_status", None),
            },
        ) from exc

    return RfpDepartmentDecisionResponse(**result)


@router.post(
    "/tickets/{ticket_id}/sections/{department_id}/regenerate",
    response_model=RfpRegenerateResponse,
)
def post_department_regenerate(
    ticket_id: str,
    department_id: str,
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> RfpRegenerateResponse:
    """Reject recovery — regenerate one department draft and re-open its approval interrupt."""
    _require_rfp_dependencies()
    try:
        result = regenerate_department_section(
            session,
            ticket_id=ticket_id,
            department_id=department_id,
        )
    except RfpTicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFP ticket not found.",
        ) from exc
    except RfpSectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFP department section not found.",
        ) from exc
    except DecisionNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "status": exc.current_status,
            },
        ) from exc

    return RfpRegenerateResponse(**result)


@router.post(
    "/tickets/{ticket_id}/ceo/decision",
    response_model=RfpCeoDecisionResponse,
)
def post_ceo_decision(
    ticket_id: str,
    body: RfpCeoDecisionRequest,
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> RfpCeoDecisionResponse:
    """CEO approve or reject after all departments and arbitration complete."""
    _require_rfp_dependencies()
    if body.decision not in CEO_DECISION_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CEO decision. Expected one of: {sorted(CEO_DECISION_VALUES)}.",
        )

    approver = (current_user.name or current_user.email or "Mariana Restrepo").strip()
    try:
        result = submit_ceo_decision(
            session,
            ticket_id=ticket_id,
            decision=body.decision,
            approver=approver,
            comment=body.comment,
        )
    except RfpTicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFP ticket not found.",
        ) from exc
    except ApprovalResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (DecisionNotAllowedError, NoPendingInterruptError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "status": getattr(exc, "current_status", None),
            },
        ) from exc

    return RfpCeoDecisionResponse(**result)


@router.get(
    "/tickets/{ticket_id}/trace",
    response_model=list[RfpTraceEventResponse],
)
def get_rfp_ticket_trace(
    ticket_id: str,
    limit: int = Query(default=500, ge=1, le=2000),
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> list[RfpTraceEventResponse]:
    """Return durable P1–P3 graph trace events for a ticket."""
    if not config.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RFP intake requires DATABASE_URL.",
        )
    try:
        return list_trace_events(session, ticket_id, limit=limit)
    except RfpTicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFP ticket not found.",
        ) from exc


@router.get(
    "/tickets/{ticket_id}/final-document",
    response_model=RfpFinalDocumentResponse,
)
def get_rfp_final_document(
    ticket_id: str,
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> RfpFinalDocumentResponse:
    """Return the merged final proposal markdown when synthesis is complete."""
    if not config.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RFP intake requires DATABASE_URL.",
        )
    try:
        result = get_final_document(session, ticket_id)
    except RfpTicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RFP ticket not found.",
        ) from exc
    except FinalDocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Final document is not available yet.",
        ) from exc

    return RfpFinalDocumentResponse(**result)
