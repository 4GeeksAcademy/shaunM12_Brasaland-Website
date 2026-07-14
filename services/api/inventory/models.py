"""SQLModel ORM tables for ingredient inventory (Supabase)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from .constants import DEFAULT_MIN_STOCK_THRESHOLD


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Ingredient(SQLModel, table=True):
    """Catalogue item. Stock is never stored here — only derived from orders."""

    __tablename__ = "ingredient"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    sku: str = Field(unique=True, index=True)
    unit: str
    category: str
    country: str
    is_active: bool = Field(default=True)
    min_stock_threshold: float = Field(default=DEFAULT_MIN_STOCK_THRESHOLD, gt=0)


class IngredientLocationSettings(SQLModel, table=True):
    """Per-restaurant override for ``Ingredient.min_stock_threshold``."""

    __tablename__ = "ingredient_location_settings"
    __table_args__ = (UniqueConstraint("ingredient_id", "location_id"),)

    id: int | None = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id", index=True)
    location_id: int = Field(index=True)
    min_stock_threshold: float = Field(gt=0)


class IngredientEntry(SQLModel, table=True):
    """Inbound delivery — increases stock."""

    __tablename__ = "ingredient_entry"

    id: int | None = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id", index=True)
    quantity: float = Field(gt=0)
    supplier_id: int = Field(index=True)
    supplier_name: str
    location_id: int
    unit_cost: float | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utc_now)
    user_uuid: str


class IngredientExit(SQLModel, table=True):
    """Outbound consumption or waste — decreases stock."""

    __tablename__ = "ingredient_exit"

    id: int | None = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id", index=True)
    quantity: float = Field(gt=0)
    reason: str
    location_id: int
    created_at: datetime = Field(default_factory=_utc_now)
    user_uuid: str


__all__ = [
    "Ingredient",
    "IngredientEntry",
    "IngredientExit",
    "IngredientLocationSettings",
]
