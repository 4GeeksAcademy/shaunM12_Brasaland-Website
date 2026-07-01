"""Seed ingredient inventory data into Supabase for local demos."""

from __future__ import annotations

from sqlmodel import Session, select

from database import get_engine
from .models import Ingredient, IngredientEntry, IngredientExit

# Default actor when seeding outside an authenticated request.
_DEFAULT_USER_UUID = "1"

_INGREDIENTS = [
    {
        "name": "Beef brisket",
        "sku": "BRS-BEEF-001",
        "unit": "kg",
        "category": "meat",
        "country": "CO",
    },
    {
        "name": "Pork ribs",
        "sku": "BRS-PORK-001",
        "unit": "kg",
        "category": "meat",
        "country": "US",
    },
    {
        "name": "Chimichurri sauce",
        "sku": "BRS-SAUCE-001",
        "unit": "litre",
        "category": "sauce",
        "country": "CO",
    },
    {
        "name": "House BBQ sauce",
        "sku": "BRS-SAUCE-002",
        "unit": "litre",
        "category": "sauce",
        "country": "US",
    },
    {
        "name": "Yuca (cassava)",
        "sku": "BRS-PROD-001",
        "unit": "kg",
        "category": "produce",
        "country": "CO",
    },
    {
        "name": "Takeaway box (M)",
        "sku": "BRS-PKG-001",
        "unit": "unit",
        "category": "packaging",
        "country": "CO",
    },
]


def seed_inventory_if_empty() -> tuple[int, int]:
    """Load demo ingredients and orders when the catalogue is empty.

    Returns ``(ingredients_added, orders_added)``.
    """
    engine = get_engine()
    with Session(engine) as session:
        if session.exec(select(Ingredient)).first() is not None:
            return 0, 0

        sku_to_id: dict[str, int] = {}
        for row in _INGREDIENTS:
            ingredient = Ingredient.model_validate(row)
            session.add(ingredient)
            session.commit()
            session.refresh(ingredient)
            assert ingredient.id is not None
            sku_to_id[ingredient.sku] = ingredient.id

        orders = [
            IngredientEntry(
                ingredient_id=sku_to_id["BRS-BEEF-001"],
                quantity=50,
                supplier_name="Carnes del Valle S.A.",
                location_id=1,
                user_uuid=_DEFAULT_USER_UUID,
            ),
            IngredientEntry(
                ingredient_id=sku_to_id["BRS-BEEF-001"],
                quantity=30,
                supplier_name="Carnes del Valle S.A.",
                location_id=1,
                user_uuid=_DEFAULT_USER_UUID,
            ),
            IngredientEntry(
                ingredient_id=sku_to_id["BRS-PORK-001"],
                quantity=40,
                supplier_name="MiamiMeat Co.",
                location_id=7,
                user_uuid=_DEFAULT_USER_UUID,
            ),
            IngredientEntry(
                ingredient_id=sku_to_id["BRS-SAUCE-001"],
                quantity=20,
                supplier_name="Salsas Artesanales Ltda.",
                location_id=2,
                user_uuid=_DEFAULT_USER_UUID,
            ),
            IngredientExit(
                ingredient_id=sku_to_id["BRS-BEEF-001"],
                quantity=25,
                reason="consumption",
                location_id=1,
                user_uuid=_DEFAULT_USER_UUID,
            ),
            IngredientExit(
                ingredient_id=sku_to_id["BRS-BEEF-001"],
                quantity=5,
                reason="waste",
                location_id=1,
                user_uuid=_DEFAULT_USER_UUID,
            ),
            IngredientExit(
                ingredient_id=sku_to_id["BRS-PORK-001"],
                quantity=10,
                reason="consumption",
                location_id=7,
                user_uuid=_DEFAULT_USER_UUID,
            ),
        ]
        for order in orders:
            session.add(order)
        session.commit()
        return len(_INGREDIENTS), len(orders)
