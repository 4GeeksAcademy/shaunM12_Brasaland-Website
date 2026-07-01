"""SQLModel ORM tables for centralized incident management."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Incident(SQLModel, table=True):
    __tablename__ = "incident"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: str
    category: str = Field(index=True)
    status: str = Field(index=True, default="open")
    origin: str = Field(index=True)
    branch: str = Field(index=True)
    created_at: datetime = Field(default_factory=_utc_now, index=True)
    updated_at: datetime = Field(default_factory=_utc_now)


class IncidentSeedKey(SQLModel, table=True):
    """Idempotency keys for seed imports without storing legacy IDs on incidents."""

    __tablename__ = "incident_seed_key"

    id: int | None = Field(default=None, primary_key=True)
    source_key: str = Field(unique=True, index=True)
    incident_id: int = Field(foreign_key="incident.id", index=True)
    created_at: datetime = Field(default_factory=_utc_now)


__all__ = ["Incident", "IncidentSeedKey"]

