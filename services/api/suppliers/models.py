"""Pydantic models for supplier directory API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from .constants import COUNTRY_CURRENCY, VALID_CATEGORIES, VALID_COUNTRIES, VALID_STATUSES

SupplierCategory = Literal[
    "meat",
    "vegetables_and_greens",
    "sauces_and_seasonings",
    "beverages",
    "packaging",
    "cleaning_products",
    "dairy",
    "carbon_and_fuel",
]

SupplierStatus = Literal["active", "suspended"]
SupplierCountry = Literal["Colombia", "USA"]
SupplierCurrency = Literal["COP", "USD"]


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1)
    country: SupplierCountry
    categories: list[SupplierCategory] = Field(min_length=1)
    rate_per_unit: float = Field(gt=0)
    currency: SupplierCurrency
    status: SupplierStatus
    contact_email: EmailStr | None = None
    notes: str | None = None

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, value: list[str]) -> list[str]:
        invalid = [item for item in value if item not in VALID_CATEGORIES]
        if invalid:
            raise ValueError(f"Invalid categories: {', '.join(invalid)}")
        return value

    @model_validator(mode="after")
    def validate_country_currency(self) -> SupplierCreate:
        expected = COUNTRY_CURRENCY[self.country]
        if self.currency != expected:
            raise ValueError(
                f"Suppliers from {self.country} must use currency {expected}"
            )
        return self


class SupplierRateUpdate(BaseModel):
    rate_per_unit: float = Field(gt=0)


class SupplierStatusUpdate(BaseModel):
    status: SupplierStatus

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(VALID_STATUSES)}")
        return value


class SupplierNotesUpdate(BaseModel):
    notes: str | None = None


class SupplierResponse(BaseModel):
    id: int
    name: str
    country: SupplierCountry
    categories: list[SupplierCategory]
    rate_per_unit: float
    currency: SupplierCurrency
    rate_updated_at: datetime
    status: SupplierStatus
    contact_email: EmailStr | None = None
    notes: str | None = None

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        if value not in VALID_COUNTRIES:
            raise ValueError(f"Country must be one of: {', '.join(VALID_COUNTRIES)}")
        return value
