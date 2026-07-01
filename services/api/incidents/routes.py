"""FastAPI routes for centralized incident manager."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlmodel import Session

from database import get_db

from . import repository
from .constants import BRANCH_VALUES, CATEGORY_VALUES, ORIGIN_VALUES, STATUS_VALUES
from .schemas import (
    IncidentCreate,
    IncidentResponse,
    IncidentStatusUpdate,
    IncidentSummaryResponse,
    parse_validation_error,
)

router = APIRouter(tags=["incidents"])


def _raise_validation_error(field: str, message: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"field": field, "message": message},
    )


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    payload: dict[str, Any],
    session: Session = Depends(get_db),
) -> IncidentResponse:
    try:
        parsed = IncidentCreate.model_validate(payload)
        return repository.create_incident(session, parsed)
    except ValidationError as exc:
        issue = parse_validation_error(exc)
        _raise_validation_error(issue.field, issue.message)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected server error. Please try again later.",
        )


@router.get("", response_model=list[IncidentResponse])
def list_incidents(
    status_filter: str | None = Query(default=None, alias="status"),
    origin: str | None = Query(default=None),
    branch: str | None = Query(default=None),
    category: str | None = Query(default=None),
    session: Session = Depends(get_db),
) -> list[IncidentResponse]:
    if status_filter is not None and status_filter not in STATUS_VALUES:
        _raise_validation_error("status", "Invalid status value.")
    if origin is not None and origin not in ORIGIN_VALUES:
        _raise_validation_error("origin", "Invalid origin value.")
    if branch is not None and branch not in BRANCH_VALUES:
        _raise_validation_error("branch", "Invalid branch value.")
    if category is not None and category not in CATEGORY_VALUES:
        _raise_validation_error("category", "Invalid category value.")

    try:
        return repository.list_incidents(
            session,
            status=status_filter,
            origin=origin,
            branch=branch,
            category=category,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected server error. Please try again later.",
        )


@router.get("/summary", response_model=IncidentSummaryResponse)
def get_summary(session: Session = Depends(get_db)) -> IncidentSummaryResponse:
    try:
        return repository.summary(session)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected server error. Please try again later.",
        )


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: int,
    session: Session = Depends(get_db),
) -> IncidentResponse:
    try:
        found = repository.get_incident(session, incident_id)
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found."
            )
        return found
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected server error. Please try again later.",
        )


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
def update_incident_status(
    incident_id: int,
    payload: dict[str, Any],
    session: Session = Depends(get_db),
) -> IncidentResponse:
    try:
        parsed = IncidentStatusUpdate.model_validate(payload)
    except ValidationError as exc:
        issue = parse_validation_error(exc)
        _raise_validation_error(issue.field, issue.message)

    try:
        return repository.update_incident_status(session, incident_id, parsed.status)
    except repository.IncidentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    except repository.InvalidTransitionError as exc:
        _raise_validation_error("status", str(exc))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected server error. Please try again later.",
        )

