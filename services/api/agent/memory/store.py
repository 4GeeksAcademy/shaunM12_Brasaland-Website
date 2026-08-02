"""Persistent memory read/write store (context-26 P26-L1d)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import Session, select

from .denylist import check_denylist
from .keys import GLOBAL_CATEGORIES
from .models import AgentMemoryAuditLog, AgentMemoryEntry, ensure_agent_memory_schema
from .schemas import MemoryProposal, MemoryWriteResult, ProposalValidationError, validate_proposal_shape

logger = logging.getLogger(__name__)

DEFAULT_CAP_PER_LOCATION = 12
DEFAULT_INJECT_MAX_ROWS = 8
DEFAULT_TTL_HOURS = 8760
DEFAULT_KNOWN_INCIDENTS_TTL_HOURS = 4320
DEFAULT_PROPOSAL_RATE_LIMIT = 20
DEFAULT_PROPOSAL_RATE_WINDOW_HOURS = 24


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r — using default %s", name, raw, default)
        return default


def cap_per_location() -> int:
    return _env_int("AGENT_MEMORY_CAP_PER_LOCATION", DEFAULT_CAP_PER_LOCATION)


def inject_max_rows() -> int:
    return _env_int("AGENT_MEMORY_INJECT_MAX_ROWS", DEFAULT_INJECT_MAX_ROWS)


def category_ttl_hours(category: str) -> int:
    if category == "known_incidents":
        return _env_int(
            "AGENT_MEMORY_KNOWN_INCIDENTS_TTL_HOURS",
            DEFAULT_KNOWN_INCIDENTS_TTL_HOURS,
        )
    return _env_int("AGENT_MEMORY_TTL_HOURS", DEFAULT_TTL_HOURS)


def proposal_rate_limit() -> int:
    return _env_int("AGENT_MEMORY_PROPOSAL_RATE_LIMIT", DEFAULT_PROPOSAL_RATE_LIMIT)


def proposal_rate_window_hours() -> int:
    return _env_int(
        "AGENT_MEMORY_PROPOSAL_RATE_WINDOW_HOURS",
        DEFAULT_PROPOSAL_RATE_WINDOW_HOURS,
    )


@dataclass(frozen=True)
class ProposalRateLimitResult:
    allowed: bool
    count: int
    limit: int


def count_recent_proposed(
    session: Session,
    user_id: int,
    *,
    window_hours: int | None = None,
) -> int:
    """Count ``proposed`` audit rows for a user inside the rate window (P26-L4h)."""
    ensure_agent_memory_schema(session)
    window = window_hours if window_hours is not None else proposal_rate_window_hours()
    cutoff = _utc_now() - timedelta(hours=window)
    statement = select(AgentMemoryAuditLog).where(
        AgentMemoryAuditLog.user_id == user_id,
        AgentMemoryAuditLog.outcome == "proposed",
        AgentMemoryAuditLog.created_at >= cutoff,
    )
    return len(session.exec(statement).all())


def check_proposal_rate_limit(
    session: Session,
    user_id: int,
) -> ProposalRateLimitResult:
    """Return whether another pending proposal may be staged (P26-L4h)."""
    limit = proposal_rate_limit()
    count = count_recent_proposed(session, user_id)
    return ProposalRateLimitResult(allowed=count < limit, count=count, limit=limit)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(expires_at: datetime | None, now: datetime) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= now


def _expires_at_for(category: str, *, now: datetime | None = None) -> datetime:
    base = now or _utc_now()
    return base + timedelta(hours=category_ttl_hours(category))


def _proposal_to_json(proposal: MemoryProposal) -> dict[str, Any]:
    return proposal.model_dump(mode="json")


def log_proposal(
    session: Session,
    *,
    user_id: int,
    outcome: str,
    proposal: MemoryProposal | dict[str, Any] | None = None,
    reason: str | None = None,
    user_message: str | None = None,
    thread_id: str | None = None,
    superseded_value: str | None = None,
) -> AgentMemoryAuditLog:
    """Append an audit row (P26-L1d, P26-L3h)."""
    ensure_agent_memory_schema(session)
    proposal_payload: dict[str, Any] = {}
    if proposal is not None:
        model = (
            proposal
            if isinstance(proposal, MemoryProposal)
            else MemoryProposal.model_validate(proposal)
        )
        proposal_payload = _proposal_to_json(model)

    row = AgentMemoryAuditLog(
        thread_id=thread_id,
        user_id=user_id,
        proposal_json=proposal_payload,
        outcome=outcome,
        reason=reason,
        user_message=user_message,
        superseded_value=superseded_value,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _find_existing_entry(
    session: Session,
    proposal: MemoryProposal,
    *,
    user_id: int,
) -> AgentMemoryEntry | None:
    if proposal.category in GLOBAL_CATEGORIES:
        statement = select(AgentMemoryEntry).where(
            AgentMemoryEntry.location_id == proposal.location_id,
            AgentMemoryEntry.category == proposal.category,
            AgentMemoryEntry.key == proposal.key,
            AgentMemoryEntry.user_id.is_(None),
        )
    else:
        statement = select(AgentMemoryEntry).where(
            AgentMemoryEntry.user_id == user_id,
            AgentMemoryEntry.category == proposal.category,
            AgentMemoryEntry.key == proposal.key,
        )
    return session.exec(statement).first()


def _count_location_entries(session: Session, location_id: int) -> int:
    now = _utc_now()
    statement = select(AgentMemoryEntry).where(
        AgentMemoryEntry.location_id == location_id,
        AgentMemoryEntry.user_id.is_(None),
        AgentMemoryEntry.category.in_(tuple(GLOBAL_CATEGORIES)),
    )
    count = 0
    for row in session.exec(statement).all():
        if _is_expired(row.expires_at, now):
            continue
        count += 1
    return count


def _load_global_entries(
    session: Session,
    location_id: int,
    *,
    now: datetime | None = None,
) -> list[AgentMemoryEntry]:
    current = now or _utc_now()
    statement = (
        select(AgentMemoryEntry)
        .where(
            AgentMemoryEntry.location_id == location_id,
            AgentMemoryEntry.user_id.is_(None),
            AgentMemoryEntry.category.in_(tuple(GLOBAL_CATEGORIES)),
        )
        .order_by(AgentMemoryEntry.approved_at.desc())
    )
    rows: list[AgentMemoryEntry] = []
    for row in session.exec(statement).all():
        if _is_expired(row.expires_at, current):
            continue
        rows.append(row)
    return rows


def _load_preference_entries(
    session: Session,
    user_id: int,
    *,
    now: datetime | None = None,
) -> list[AgentMemoryEntry]:
    current = now or _utc_now()
    statement = (
        select(AgentMemoryEntry)
        .where(
            AgentMemoryEntry.user_id == user_id,
            AgentMemoryEntry.category == "preferences",
        )
        .order_by(AgentMemoryEntry.approved_at.desc())
    )
    rows: list[AgentMemoryEntry] = []
    for row in session.exec(statement).all():
        if _is_expired(row.expires_at, current):
            continue
        rows.append(row)
    return rows


def purge_stale_entries(
    session: Session,
    *,
    grace_days: int = 30,
) -> int:
    """Delete entries expired longer than ``grace_days`` ago (P26-L3g stretch)."""
    ensure_agent_memory_schema(session)
    cutoff = _utc_now() - timedelta(days=grace_days)
    statement = select(AgentMemoryEntry)
    removed = 0
    for row in session.exec(statement).all():
        if row.expires_at is None:
            continue
        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < cutoff:
            session.delete(row)
            removed += 1
    if removed:
        session.commit()
    return removed


def write_memory(
    session: Session,
    *,
    proposal: MemoryProposal | dict[str, Any],
    approved_by: int,
    outcome: str = "approved",
) -> MemoryWriteResult:
    """Persist an approved fact after validation and denylist (P26-L4e)."""
    ensure_agent_memory_schema(session)
    if approved_by <= 0:
        return MemoryWriteResult(ok=False, outcome="rejected", reason="invalid_approved_by")

    try:
        validated = validate_proposal_shape(proposal)
    except ProposalValidationError as exc:
        shape_reasons = {"invalid_key", "invalid_category", "invalid_location_id", "location_id_required"}
        outcome = "rejected" if exc.reason in shape_reasons else "rejected_denylist"
        log_proposal(
            session,
            user_id=approved_by,
            outcome=outcome,
            proposal=proposal,
            reason=exc.reason,
        )
        return MemoryWriteResult(ok=False, outcome=outcome, reason=exc.reason)

    denylist = check_denylist(
        category=validated.category,
        value=validated.value,
        reason=validated.reason,
    )
    if denylist.blocked:
        log_proposal(
            session,
            user_id=approved_by,
            outcome="rejected_denylist",
            proposal=validated,
            reason=denylist.reason,
        )
        return MemoryWriteResult(ok=False, outcome="rejected_denylist", reason=denylist.reason)

    existing = _find_existing_entry(session, validated, user_id=approved_by)
    superseded_value = existing.value if existing else None

    if (
        validated.category in GLOBAL_CATEGORIES
        and existing is None
        and validated.location_id is not None
        and _count_location_entries(session, validated.location_id) >= cap_per_location()
    ):
        log_proposal(
            session,
            user_id=approved_by,
            outcome="rejected_cap_exceeded",
            proposal=validated,
            reason="cap_exceeded",
        )
        return MemoryWriteResult(
            ok=False,
            outcome="rejected_cap_exceeded",
            reason="cap_exceeded",
        )

    now = _utc_now()
    expires_at = _expires_at_for(validated.category, now=now)

    if validated.category in GLOBAL_CATEGORIES:
        row = existing or AgentMemoryEntry(
            location_id=validated.location_id,
            user_id=None,
            category=validated.category,
            key=validated.key,
        )
    else:
        row = existing or AgentMemoryEntry(
            location_id=None,
            user_id=approved_by,
            category=validated.category,
            key=validated.key,
        )

    row.value = validated.value
    row.source = "user_confirmed"
    row.approved_by = approved_by
    row.approved_at = now
    row.expires_at = expires_at

    session.add(row)
    session.commit()
    session.refresh(row)

    log_proposal(
        session,
        user_id=approved_by,
        outcome=outcome,
        proposal=validated,
        superseded_value=superseded_value,
    )

    return MemoryWriteResult(
        ok=True,
        entry_id=row.id,
        outcome=outcome,
        superseded_value=superseded_value,
    )


def filter_entries_for_location(
    entries: list[AgentMemoryEntry],
    location_id: int | None,
) -> list[AgentMemoryEntry]:
    """Hard guard: global memory rows must match the resolved location scope."""
    if location_id is None:
        return [row for row in entries if row.location_id is None]
    filtered: list[AgentMemoryEntry] = []
    for row in entries:
        if row.location_id is None:
            filtered.append(row)
        elif row.location_id == location_id:
            filtered.append(row)
    return filtered


def read_memory(
    session: Session,
    *,
    user_id: int | None = None,
    location_id: int | None = None,
    max_rows: int | None = None,
) -> list[AgentMemoryEntry]:
    """Load non-expired memory rows for prompt injection (P26-L7e, P26-L3f, P26-L12c).

    Priority within ``max_rows``: location-scoped global facts first, then user preferences.
    """
    ensure_agent_memory_schema(session)
    limit = max_rows if max_rows is not None else inject_max_rows()
    now = _utc_now()

    rows: list[AgentMemoryEntry] = []
    if location_id is not None:
        rows.extend(_load_global_entries(session, location_id, now=now))

    if user_id is not None:
        pref_rows = _load_preference_entries(session, user_id, now=now)
        remaining = limit - len(rows)
        if remaining > 0:
            rows.extend(pref_rows[:remaining])

    rows = filter_entries_for_location(rows, location_id)
    return rows[:limit]


def format_memory_context(
    entries: list[AgentMemoryEntry],
    *,
    scoped_location_id: int | None = None,
) -> str:
    """Format approved rows for generation prompt (P26-L4f, P26-L15b)."""
    if not entries:
        return ""
    if scoped_location_id is not None:
        entries = filter_entries_for_location(entries, scoped_location_id)
    if not entries:
        return ""

    lines: list[str] = []
    if scoped_location_id is not None:
        from packages.shared.restaurant_locations import format_location_label, location_short_name

        short = location_short_name(scoped_location_id)
        label = format_location_label(scoped_location_id)
        lines.append(
            f"Scoped to location_id={scoped_location_id} ({short}; {label}). "
            "Do not apply these rows to other locations."
        )
    for row in entries:
        location_suffix = (
            f"location_id={row.location_id}" if row.location_id is not None else "user_preference"
        )
        lines.append(
            f"- [{location_suffix} category={row.category} key={row.key}] {row.value}"
        )
    return "\n".join(lines)
