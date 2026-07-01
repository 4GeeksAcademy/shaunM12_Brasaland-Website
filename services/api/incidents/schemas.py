"""Pydantic request/response schemas for incident manager endpoints."""

from __future__ import annotations

from datetime import datetime
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from .constants import BRANCH_VALUES, CATEGORY_VALUES, ORIGIN_VALUES, STATUS_VALUES

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from packages.shared.incidents_validation import validate_enum_value

IncidentBranch = Literal[
    "central",
    "medellin_centro",
    "medellin_laureles",
    "medellin_envigado",
    "medellin_bello",
    "medellin_itagui",
    "bogota_chapinero",
    "bogota_usaquen",
    "cali_granada",
    "barranquilla_norte",
    "miami_doral",
    "miami_hialeah",
    "miami_kendall",
    "orlando_international",
    "fort_lauderdale",
]

IncidentCategory = Literal[
    "equipment_failure",
    "supply_issue",
    "customer_complaint",
    "staff_issue",
    "facility_issue",
    "pos_system",
    "delivery_issue",
    "other",
]

IncidentOrigin = Literal["customer", "branch", "internal"]
IncidentStatus = Literal["open", "in_progress", "resolved", "discarded"]


class ValidationMessage(BaseModel):
    field: str
    message: str


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: IncidentCategory
    status: IncidentStatus = "open"
    origin: IncidentOrigin
    branch: IncidentBranch
    created_at: datetime | None = None

    @field_validator("title", "description")
    @classmethod
    def non_empty_trimmed(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return validate_enum_value(value, CATEGORY_VALUES, "Invalid category value.")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return validate_enum_value(value, STATUS_VALUES, "Invalid status value.")

    @field_validator("origin")
    @classmethod
    def validate_origin(cls, value: str) -> str:
        return validate_enum_value(value, ORIGIN_VALUES, "Invalid origin value.")

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, value: str) -> str:
        return validate_enum_value(value, BRANCH_VALUES, "Invalid branch value.")


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return validate_enum_value(value, STATUS_VALUES, "Invalid status value.")


class IncidentResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    status: str
    origin: str
    branch: str
    created_at: datetime
    updated_at: datetime


class IncidentSummaryResponse(BaseModel):
    by_status: dict[str, int]
    by_category: dict[str, int]
    by_origin: dict[str, int]
    by_branch: dict[str, int]


def parse_validation_error(exc: ValidationError) -> ValidationMessage:
    issue = exc.errors()[0] if exc.errors() else {"loc": ("body",), "msg": "Invalid input."}
    loc = issue.get("loc", ("body",))
    field = str(loc[-1]) if isinstance(loc, (tuple, list)) and loc else "body"
    message = str(issue.get("msg", "Invalid input."))
    return ValidationMessage(field=field, message=message)

