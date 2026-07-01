"""Pydantic request/response schemas for the inventory API.

Separate from ``inventory.models`` — endpoints must return these, never raw ORM
rows. ``current_stock`` appears only on product responses (computed).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .constants import (
    MAX_LOCATION_ID,
    MIN_LOCATION_ID,
    VALID_CATEGORIES,
    VALID_COUNTRIES,
    VALID_EXIT_REASONS,
)

ProductCategory = Literal[
    "meat", "seafood", "produce", "sauce", "beverage", "packaging", "cleaning"
]
ProductCountry = Literal["CO", "US"]
ExitReason = Literal["consumption", "waste"]


def _validate_location(value: int) -> int:
    if not MIN_LOCATION_ID <= value <= MAX_LOCATION_ID:
        raise ValueError(
            f"location_id must be between {MIN_LOCATION_ID} and {MAX_LOCATION_ID}"
        )
    return value


class ProductCreate(BaseModel):
    name: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    category: ProductCategory
    country: ProductCountry = "CO"
    is_active: bool = True

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category: {value}")
        return value

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        if value not in VALID_COUNTRIES:
            raise ValueError(f"country must be one of: {', '.join(VALID_COUNTRIES)}")
        return value


class ProductResponse(BaseModel):
    id: int
    name: str
    sku: str
    unit: str
    category: str
    country: str
    is_active: bool
    current_stock: float


class ProductUpdate(BaseModel):
    is_active: bool


class InboundOrderCreate(BaseModel):
    ingredient_id: int
    quantity: float = Field(gt=0)
    supplier_name: str = Field(min_length=1)
    location_id: int

    @field_validator("location_id")
    @classmethod
    def validate_location(cls, value: int) -> int:
        return _validate_location(value)


class OutboundOrderCreate(BaseModel):
    ingredient_id: int
    quantity: float = Field(gt=0)
    reason: ExitReason
    location_id: int

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if value not in VALID_EXIT_REASONS:
            raise ValueError(
                f"reason must be one of: {', '.join(VALID_EXIT_REASONS)}"
            )
        return value

    @field_validator("location_id")
    @classmethod
    def validate_location(cls, value: int) -> int:
        return _validate_location(value)


class InboundOrderResponse(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    ingredient_sku: str
    quantity: float
    supplier_name: str
    location_id: int
    created_at: datetime
    user_uuid: str


class OutboundOrderResponse(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    ingredient_sku: str
    quantity: float
    reason: str
    location_id: int
    created_at: datetime
    user_uuid: str


class OrdersListResponse(BaseModel):
    inbound: list[InboundOrderResponse]
    outbound: list[OutboundOrderResponse]
