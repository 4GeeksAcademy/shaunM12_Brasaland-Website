"""Seed ingredient inventory data into Supabase for local demos."""

from __future__ import annotations

import sys

from sqlmodel import Session, select
from sqlalchemy import text

from database import get_engine
from .models import Ingredient, IngredientEntry, IngredientExit
from .seed_data import DEMO_ORDERS, INGREDIENTS

# Default actor when seeding outside an authenticated request.
_DEFAULT_USER_UUID = "1"

_INACTIVE_SKUS = frozenset({
    "BRS-OCT-001",
    "BRS-CRAB-001",
    "BRS-FISH-007",
    "BRS-PKG-010",
})


def ensure_inventory_schema(session: Session) -> None:
    """Apply additive schema updates that ``create_all`` skips on existing tables."""
    session.connection().execute(
        text(
            "ALTER TABLE ingredient "
            "ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"
        )
    )
    for sku in _INACTIVE_SKUS:
        session.connection().execute(
            text("UPDATE ingredient SET is_active = FALSE WHERE sku = :sku"),
            {"sku": sku},
        )
    session.commit()


def purge_test_ingredients() -> int:
    """Remove pytest catalogue rows (SKU prefix ``TEST-``) and their orders."""
    engine = get_engine()
    with Session(engine) as session:
        test_ids = session.exec(
            select(Ingredient.id).where(Ingredient.sku.like("TEST-%"))  # type: ignore[attr-defined]
        ).all()
        if not test_ids:
            return 0
        id_list = list(test_ids)
        session.connection().execute(
            text(
                "DELETE FROM ingredient_exit WHERE ingredient_id = ANY(:ids)"
            ),
            {"ids": id_list},
        )
        session.connection().execute(
            text(
                "DELETE FROM ingredient_entry WHERE ingredient_id = ANY(:ids)"
            ),
            {"ids": id_list},
        )
        session.connection().execute(
            text("DELETE FROM ingredient WHERE id = ANY(:ids)"),
            {"ids": id_list},
        )
        session.commit()
        return len(id_list)


def reset_inventory_tables(session: Session) -> None:
    """Remove all inventory rows (exits → entries → ingredients)."""
    session.connection().execute(
        text(
            "TRUNCATE ingredient_exit, ingredient_entry, ingredient "
            "RESTART IDENTITY CASCADE"
        )
    )
    session.commit()


def _seed_inventory_session(session: Session) -> tuple[int, int]:
    sku_to_id: dict[str, int] = {}
    for row in INGREDIENTS:
        ingredient = Ingredient.model_validate(row)
        session.add(ingredient)
        session.commit()
        session.refresh(ingredient)
        assert ingredient.id is not None
        sku_to_id[ingredient.sku] = ingredient.id

    orders: list[IngredientEntry | IngredientExit] = []
    for spec in DEMO_ORDERS:
        sku = spec["sku"]
        ingredient_id = sku_to_id[sku]
        if spec["kind"] == "inbound":
            orders.append(
                IngredientEntry(
                    ingredient_id=ingredient_id,
                    quantity=spec["quantity"],
                    supplier_name=spec["supplier_name"],
                    location_id=spec["location_id"],
                    user_uuid=_DEFAULT_USER_UUID,
                )
            )
        else:
            orders.append(
                IngredientExit(
                    ingredient_id=ingredient_id,
                    quantity=spec["quantity"],
                    reason=spec["reason"],
                    location_id=spec["location_id"],
                    user_uuid=_DEFAULT_USER_UUID,
                )
            )

    for order in orders:
        session.add(order)
    session.commit()
    return len(INGREDIENTS), len(orders)


def seed_inventory_if_empty() -> tuple[int, int]:
    """Load demo ingredients and orders when the catalogue is empty.

    Returns ``(ingredients_added, orders_added)``.
    """
    engine = get_engine()
    with Session(engine) as session:
        ensure_inventory_schema(session)
        if session.exec(select(Ingredient)).first() is not None:
            return 0, 0
        return _seed_inventory_session(session)


def reset_and_seed_inventory() -> tuple[int, int]:
    """Wipe all inventory tables and load the full Brasaland demo catalogue."""
    engine = get_engine()
    with Session(engine) as session:
        ensure_inventory_schema(session)
        reset_inventory_tables(session)
        return _seed_inventory_session(session)


def main() -> int:
    """CLI: full inventory reset + reseed (requires ``DATABASE_URL``)."""
    try:
        ingredients, orders = reset_and_seed_inventory()
    except RuntimeError as exc:
        print(f"Inventory seed failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Inventory reset complete: {ingredients} ingredient(s), "
        f"{orders} order row(s) seeded."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
