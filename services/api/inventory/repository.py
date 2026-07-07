"""Persistence and stock logic for ingredient inventory (Supabase)."""

from __future__ import annotations

from sqlmodel import Session, select, func

from .constants import (
    DEFAULT_MIN_STOCK_THRESHOLD,
    country_for_location,
)
from .supplier_validation import (
    SupplierCountryMismatchError,
    SupplierInactiveError,
    SupplierNotFoundError,
    resolve_inbound_supplier,
)
from .models import Ingredient, IngredientEntry, IngredientExit, IngredientLocationSettings
from .schemas import (
    InboundOrderCreate,
    InboundOrderResponse,
    OrdersListResponse,
    OutboundOrderCreate,
    OutboundOrderResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

from telemetry.context import EmitContext
from telemetry.stock import maybe_emit_stock_threshold_triggered


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


def compute_current_stock(
    session: Session,
    ingredient_id: int,
    location_id: int | None = None,
) -> float:
    """Net stock = sum(inbound) − sum(outbound), optionally scoped to one restaurant."""
    inbound_query = select(func.coalesce(func.sum(IngredientEntry.quantity), 0)).where(
        IngredientEntry.ingredient_id == ingredient_id
    )
    outbound_query = select(func.coalesce(func.sum(IngredientExit.quantity), 0)).where(
        IngredientExit.ingredient_id == ingredient_id
    )
    if location_id is not None:
        inbound_query = inbound_query.where(IngredientEntry.location_id == location_id)
        outbound_query = outbound_query.where(IngredientExit.location_id == location_id)

    inbound = session.exec(inbound_query).one()
    outbound = session.exec(outbound_query).one()
    return float(inbound) - float(outbound)


def resolve_min_stock_threshold(
    session: Session,
    ingredient: Ingredient,
    location_id: int | None = None,
) -> float:
    """Location override → ingredient default → system default."""
    assert ingredient.id is not None
    if location_id is not None:
        country_for_location(location_id)
        override = session.exec(
            select(IngredientLocationSettings).where(
                IngredientLocationSettings.ingredient_id == ingredient.id,
                IngredientLocationSettings.location_id == location_id,
            )
        ).first()
        if override is not None:
            return float(override.min_stock_threshold)
    return float(ingredient.min_stock_threshold or DEFAULT_MIN_STOCK_THRESHOLD)


def _to_product_response(
    session: Session,
    ingredient: Ingredient,
    location_id: int | None = None,
) -> ProductResponse:
    assert ingredient.id is not None
    return ProductResponse(
        id=ingredient.id,
        name=ingredient.name,
        sku=ingredient.sku,
        unit=ingredient.unit,
        category=ingredient.category,
        country=ingredient.country,
        is_active=ingredient.is_active,
        current_stock=compute_current_stock(session, ingredient.id, location_id),
        min_stock_threshold=resolve_min_stock_threshold(
            session, ingredient, location_id
        ),
    )


def create_ingredient(session: Session, payload: ProductCreate) -> ProductResponse:
    existing = session.exec(
        select(Ingredient).where(Ingredient.sku == payload.sku)
    ).first()
    if existing is not None:
        raise DuplicateSkuError(f"SKU already exists: {payload.sku}")

    ingredient = Ingredient(
        **{
            **payload.model_dump(exclude={"min_stock_threshold"}),
            "min_stock_threshold": payload.resolved_min_stock_threshold(),
        }
    )
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return _to_product_response(session, ingredient)


def get_ingredient(
    session: Session,
    ingredient_id: int,
    location_id: int | None = None,
) -> ProductResponse | None:
    ingredient = session.get(Ingredient, ingredient_id)
    if ingredient is None:
        return None
    return _to_product_response(session, ingredient, location_id)


def list_ingredients(
    session: Session,
    *,
    location_id: int | None = None,
    include_inactive: bool = False,
) -> list[ProductResponse]:
    query = select(Ingredient)
    if not include_inactive:
        query = query.where(Ingredient.is_active.is_(True))
    if location_id is not None:
        country_for_location(location_id)
    ingredients = session.exec(query.order_by(Ingredient.sku)).all()
    return [_to_product_response(session, item, location_id) for item in ingredients]


def update_ingredient(
    session: Session,
    ingredient_id: int,
    payload: ProductUpdate,
    location_id: int | None = None,
) -> ProductResponse:
    ingredient = _require_ingredient(session, ingredient_id)
    ingredient.is_active = payload.is_active
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return _to_product_response(session, ingredient, location_id)


def _require_ingredient(session: Session, ingredient_id: int) -> Ingredient:
    ingredient = session.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise IngredientNotFoundError(f"Ingredient not found: {ingredient_id}")
    return ingredient


def create_inbound_order(
    session: Session,
    payload: InboundOrderCreate,
    user_uuid: str,
    *,
    telemetry_ctx: EmitContext | None = None,
) -> InboundOrderResponse:
    ingredient = _require_ingredient(session, payload.ingredient_id)
    assert ingredient.id is not None
    stock_before = compute_current_stock(
        session, ingredient.id, location_id=payload.location_id
    )
    threshold = resolve_min_stock_threshold(session, ingredient, payload.location_id)
    supplier_id, supplier_name = resolve_inbound_supplier(
        payload,
        ingredient_category=ingredient.category,
    )
    entry = IngredientEntry(
        ingredient_id=payload.ingredient_id,
        quantity=payload.quantity,
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        location_id=payload.location_id,
        user_uuid=user_uuid,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    assert entry.id is not None
    stock_after = compute_current_stock(
        session, ingredient.id, location_id=payload.location_id
    )
    maybe_emit_stock_threshold_triggered(
        session,
        ingredient_id=ingredient.id,
        location_id=payload.location_id,
        stock_before=stock_before,
        stock_after=stock_after,
        min_stock_threshold=threshold,
        triggering_order_type="SupplyOrder",
        triggering_order_id=entry.id,
        ctx=telemetry_ctx,
    )
    return InboundOrderResponse(
        id=entry.id,
        ingredient_id=entry.ingredient_id,
        ingredient_name=ingredient.name,
        ingredient_sku=ingredient.sku,
        quantity=entry.quantity,
        supplier_id=entry.supplier_id,
        supplier_name=entry.supplier_name,
        location_id=entry.location_id,
        created_at=entry.created_at,
        user_uuid=entry.user_uuid,
    )


def create_outbound_order(
    session: Session,
    payload: OutboundOrderCreate,
    user_uuid: str,
    *,
    telemetry_ctx: EmitContext | None = None,
) -> OutboundOrderResponse:
    ingredient = _require_ingredient(session, payload.ingredient_id)
    assert ingredient.id is not None
    stock_before = compute_current_stock(
        session, ingredient.id, location_id=payload.location_id
    )
    threshold = resolve_min_stock_threshold(session, ingredient, payload.location_id)
    available = stock_before
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
    stock_after = compute_current_stock(
        session, ingredient.id, location_id=payload.location_id
    )
    maybe_emit_stock_threshold_triggered(
        session,
        ingredient_id=ingredient.id,
        location_id=payload.location_id,
        stock_before=stock_before,
        stock_after=stock_after,
        min_stock_threshold=threshold,
        triggering_order_type="ConsumptionOrder",
        triggering_order_id=exit_row.id,
        ctx=telemetry_ctx,
    )
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
                supplier_id=entry.supplier_id,
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
