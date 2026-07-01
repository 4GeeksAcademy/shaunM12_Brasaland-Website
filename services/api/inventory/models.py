"""SQLModel ORM tables for ingredient inventory (Supabase)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


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


class IngredientEntry(SQLModel, table=True):
    """Inbound delivery — increases stock."""

    __tablename__ = "ingredient_entry"

    id: int | None = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id", index=True)
    quantity: float = Field(gt=0)
    supplier_name: str
    location_id: int
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


__all__ = ["Ingredient", "IngredientEntry", "IngredientExit"]
