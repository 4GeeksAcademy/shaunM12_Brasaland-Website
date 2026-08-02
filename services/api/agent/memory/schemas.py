"""Pydantic schemas for memory proposals and validation (context-26 P26-L8 prep)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from packages.shared.restaurant_locations import get_location

from .denylist import check_denylist
from .keys import GLOBAL_CATEGORIES, MemoryKeyError, validate_category, validate_key
from .location_hint import reconcile_proposal_location_id


class MemoryProposal(BaseModel):
    location_id: int | None = None
    category: str
    key: str
    value: str = Field(min_length=1)
    reason: str | None = None

    @field_validator("value")
    @classmethod
    def value_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned


class MemoryWriteResult(BaseModel):
    ok: bool
    entry_id: int | None = None
    outcome: str
    reason: str | None = None
    superseded_value: str | None = None


class GenerationResult(BaseModel):
    """Structured Support Agent generation output (P26-L8)."""

    answer: str
    memory_proposal: MemoryProposal | None = None
    proposal_trace: str | None = None


class ProposalValidationError(ValueError):
    """Raised when a proposal fails shape, key, location, or denylist checks."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def validate_proposal_shape(
    proposal: MemoryProposal | dict[str, Any],
    *,
    question: str | None = None,
) -> MemoryProposal:
    """Validate proposal fields before pending or write (P26-L8b, P26-L2, P26-L18)."""
    model = (
        proposal
        if isinstance(proposal, MemoryProposal)
        else MemoryProposal.model_validate(proposal)
    )

    try:
        category = validate_category(model.category)
    except MemoryKeyError as exc:
        raise ProposalValidationError("invalid_category") from exc

    try:
        key = validate_key(category, model.key)
    except MemoryKeyError as exc:
        raise ProposalValidationError("invalid_key") from exc

    location_id = model.location_id
    if question:
        location_id = reconcile_proposal_location_id(
            location_id,
            question,
            category=category,
        )

    if category in GLOBAL_CATEGORIES:
        if location_id is None:
            raise ProposalValidationError("location_id_required")
        if get_location(location_id) is None:
            raise ProposalValidationError("invalid_location_id")
    elif location_id is not None and get_location(location_id) is None:
        raise ProposalValidationError("invalid_location_id")

    denylist = check_denylist(category=category, value=model.value, reason=model.reason)
    if denylist.blocked:
        raise ProposalValidationError(denylist.reason or "rejected_denylist")

    return MemoryProposal(
        location_id=location_id,
        category=category,
        key=key,
        value=model.value.strip(),
        reason=(model.reason or "").strip() or None,
    )
