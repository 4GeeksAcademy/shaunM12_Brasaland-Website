"""Persistence and stock logic for ingredient inventory (Supabase)."""

from __future__ import annotations

from sqlmodel import Session, select, func

from .models import Ingredient, IngredientEntry, IngredientExit
from .schemas import (
    InboundOrderCreate,
    InboundOrderResponse,
    OrdersListResponse,
    OutboundOrderCreate,
    OutboundOrderResponse,
    ProductCreate,
    ProductResponse,
)


class DuplicateSkuError(ValueError):
    """Raised when creating an ingredient with an existing SKU."""


class IngredientNotFoundError(ValueError):
    """Raised when an ingredient id does not exist."""


class InsufficientStockError(ValueError):
    """Raised when an outbound order would drive stock negative."""

    def __init__(self, name: str, available: float, requested: float) -> None:
        self.name = name
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient stock for ingredient '{name}'. "
            f"Available: {available}, requested: {requested}."
        )


def compute_current_stock(session: Session, ingredient_id: int) -> float:
    """Net stock = sum(inbound) − sum(outbound) for one ingredient."""
    inbound = session.exec(
        select(func.coalesce(func.sum(IngredientEntry.quantity), 0)).where(
            IngredientEntry.ingredient_id == ingredient_id
        )
    ).one()
    outbound = session.exec(
        select(func.coalesce(func.sum(IngredientExit.quantity), 0)).where(
            IngredientExit.ingredient_id == ingredient_id
        )
    ).one()
    return float(inbound) - float(outbound)


def _to_product_response(session: Session, ingredient: Ingredient) -> ProductResponse:
    assert ingredient.id is not None
    return ProductResponse(
        id=ingredient.id,
        name=ingredient.name,
        sku=ingredient.sku,
        unit=ingredient.unit,
        category=ingredient.category,
        country=ingredient.country,
        current_stock=compute_current_stock(session, ingredient.id),
    )


def create_ingredient(session: Session, payload: ProductCreate) -> ProductResponse:
    existing = session.exec(
        select(Ingredient).where(Ingredient.sku == payload.sku)
    ).first()
    if existing is not None:
        raise DuplicateSkuError(f"SKU already exists: {payload.sku}")

    ingredient = Ingredient.model_validate(payload.model_dump())
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return _to_product_response(session, ingredient)


def get_ingredient(session: Session, ingredient_id: int) -> ProductResponse | None:
    ingredient = session.get(Ingredient, ingredient_id)
    if ingredient is None:
        return None
    return _to_product_response(session, ingredient)


def list_ingredients(session: Session) -> list[ProductResponse]:
    ingredients = session.exec(select(Ingredient).order_by(Ingredient.sku)).all()
    return [_to_product_response(session, item) for item in ingredients]


def _require_ingredient(session: Session, ingredient_id: int) -> Ingredient:
    ingredient = session.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise IngredientNotFoundError(f"Ingredient not found: {ingredient_id}")
    return ingredient


def create_inbound_order(
    session: Session,
    payload: InboundOrderCreate,
    user_uuid: str,
) -> InboundOrderResponse:
    ingredient = _require_ingredient(session, payload.ingredient_id)
    entry = IngredientEntry(
        ingredient_id=payload.ingredient_id,
        quantity=payload.quantity,
        supplier_name=payload.supplier_name,
        location_id=payload.location_id,
        user_uuid=user_uuid,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    assert entry.id is not None
    return InboundOrderResponse(
        id=entry.id,
        ingredient_id=entry.ingredient_id,
        ingredient_name=ingredient.name,
        ingredient_sku=ingredient.sku,
        quantity=entry.quantity,
        supplier_name=entry.supplier_name,
        location_id=entry.location_id,
        created_at=entry.created_at,
        user_uuid=entry.user_uuid,
    )


def create_outbound_order(
    session: Session,
    payload: OutboundOrderCreate,
    user_uuid: str,
) -> OutboundOrderResponse:
    ingredient = _require_ingredient(session, payload.ingredient_id)
    assert ingredient.id is not None
    available = compute_current_stock(session, ingredient.id)
    if payload.quantity > available:
        raise InsufficientStockError(ingredient.name, available, payload.quantity)

    exit_row = IngredientExit(
        ingredient_id=payload.ingredient_id,
        quantity=payload.quantity,
        reason=payload.reason,
        location_id=payload.location_id,
        user_uuid=user_uuid,
    )
    session.add(exit_row)
    session.commit()
    session.refresh(exit_row)
    assert exit_row.id is not None
    return OutboundOrderResponse(
        id=exit_row.id,
        ingredient_id=exit_row.ingredient_id,
        ingredient_name=ingredient.name,
        ingredient_sku=ingredient.sku,
        quantity=exit_row.quantity,
        reason=exit_row.reason,
        location_id=exit_row.location_id,
        created_at=exit_row.created_at,
        user_uuid=exit_row.user_uuid,
    )


def list_orders(session: Session) -> OrdersListResponse:
    entries = session.exec(
        select(IngredientEntry).order_by(IngredientEntry.created_at)
    ).all()
    exits = session.exec(
        select(IngredientExit).order_by(IngredientExit.created_at)
    ).all()

    inbound: list[InboundOrderResponse] = []
    for entry in entries:
        ingredient = session.get(Ingredient, entry.ingredient_id)
        if ingredient is None or entry.id is None:
            continue
        inbound.append(
            InboundOrderResponse(
                id=entry.id,
                ingredient_id=entry.ingredient_id,
                ingredient_name=ingredient.name,
                ingredient_sku=ingredient.sku,
                quantity=entry.quantity,
                supplier_name=entry.supplier_name,
                location_id=entry.location_id,
                created_at=entry.created_at,
                user_uuid=entry.user_uuid,
            )
        )

    outbound: list[OutboundOrderResponse] = []
    for exit_row in exits:
        ingredient = session.get(Ingredient, exit_row.ingredient_id)
        if ingredient is None or exit_row.id is None:
            continue
        outbound.append(
            OutboundOrderResponse(
                id=exit_row.id,
                ingredient_id=exit_row.ingredient_id,
                ingredient_name=ingredient.name,
                ingredient_sku=ingredient.sku,
                quantity=exit_row.quantity,
                reason=exit_row.reason,
                location_id=exit_row.location_id,
                created_at=exit_row.created_at,
                user_uuid=exit_row.user_uuid,
            )
        )

    return OrdersListResponse(inbound=inbound, outbound=outbound)
