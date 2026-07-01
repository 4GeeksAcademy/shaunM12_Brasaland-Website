"""Persistence and aggregation logic for incidents."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, func, select

from .constants import (
    BRANCH_VALUES,
    CATEGORY_VALUES,
    ORIGIN_VALUES,
    STATUS_TRANSITIONS,
    STATUS_VALUES,
)
from .models import Incident, IncidentSeedKey
from .schemas import IncidentCreate, IncidentResponse, IncidentSummaryResponse


class IncidentNotFoundError(ValueError):
    """Raised when an incident id is missing."""


class InvalidTransitionError(ValueError):
    """Raised when a status change violates the incident lifecycle."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_response(row: Incident) -> IncidentResponse:
    assert row.id is not None
    return IncidentResponse(
        id=row.id,
        title=row.title,
        description=row.description,
        category=row.category,
        status=row.status,
        origin=row.origin,
        branch=row.branch,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def create_incident(session: Session, payload: IncidentCreate) -> IncidentResponse:
    row = Incident(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        status=payload.status,
        origin=payload.origin,
        branch=payload.branch,
        created_at=payload.created_at or _utc_now(),
        updated_at=_utc_now(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_response(row)


def list_incidents(
    session: Session,
    *,
    status: str | None = None,
    origin: str | None = None,
    branch: str | None = None,
    category: str | None = None,
) -> list[IncidentResponse]:
    query = select(Incident)
    if status is not None:
        query = query.where(Incident.status == status)
    if origin is not None:
        query = query.where(Incident.origin == origin)
    if branch is not None:
        query = query.where(Incident.branch == branch)
    if category is not None:
        query = query.where(Incident.category == category)

    rows = session.exec(query.order_by(Incident.created_at.desc())).all()
    return [_to_response(row) for row in rows]


def get_incident(session: Session, incident_id: int) -> IncidentResponse | None:
    row = session.get(Incident, incident_id)
    return _to_response(row) if row is not None else None


def update_incident_status(
    session: Session, incident_id: int, next_status: str
) -> IncidentResponse:
    row = session.get(Incident, incident_id)
    if row is None:
        raise IncidentNotFoundError(f"Incident not found: {incident_id}")

    allowed_targets = STATUS_TRANSITIONS.get(row.status, ())
    if next_status not in allowed_targets:
        raise InvalidTransitionError(
            f"Invalid status transition from '{row.status}' to '{next_status}'."
        )

    row.status = next_status
    row.updated_at = _utc_now()
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_response(row)


def summary(session: Session) -> IncidentSummaryResponse:
    by_status = {value: 0 for value in STATUS_VALUES}
    by_category = {value: 0 for value in CATEGORY_VALUES}
    by_origin = {value: 0 for value in ORIGIN_VALUES}
    by_branch = {value: 0 for value in BRANCH_VALUES}

    for status_value, count in session.exec(
        select(Incident.status, func.count(Incident.id)).group_by(Incident.status)
    ):
        by_status[str(status_value)] = int(count)

    for category_value, count in session.exec(
        select(Incident.category, func.count(Incident.id)).group_by(Incident.category)
    ):
        by_category[str(category_value)] = int(count)

    for origin_value, count in session.exec(
        select(Incident.origin, func.count(Incident.id)).group_by(Incident.origin)
    ):
        by_origin[str(origin_value)] = int(count)

    for branch_value, count in session.exec(
        select(Incident.branch, func.count(Incident.id)).group_by(Incident.branch)
    ):
        by_branch[str(branch_value)] = int(count)

    return IncidentSummaryResponse(
        by_status=by_status,
        by_category=by_category,
        by_origin=by_origin,
        by_branch=by_branch,
    )


def has_seed_key(session: Session, source_key: str) -> bool:
    return (
        session.exec(
            select(IncidentSeedKey).where(IncidentSeedKey.source_key == source_key)
        ).first()
        is not None
    )


def create_seeded_incident(
    session: Session, payload: IncidentCreate, *, source_key: str
) -> IncidentResponse:
    created = create_incident(session, payload)
    seed_key = IncidentSeedKey(source_key=source_key, incident_id=created.id)
    session.add(seed_key)
    session.commit()
    return created

