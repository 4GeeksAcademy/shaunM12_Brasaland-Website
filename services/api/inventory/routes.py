"""FastAPI routes for ingredient inventory (Supabase)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session

from auth.dependencies import get_current_user
from database import get_db
from telemetry.constants import STOCK_MUTATION_FIELDS
from telemetry.context import EmitContext
from telemetry.emit import emit_event
from telemetry.price import maybe_emit_ingredient_price_variance
from users.models import UserResponse
from . import repository
from .supplier_validation import (
    SupplierCountryMismatchError,
    SupplierInactiveError,
    SupplierNotFoundError,
)
from .constants import country_for_location
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

router = APIRouter(tags=["inventory"])


def _request_id_from_header(request: Request | None) -> str | None:
    if request is None:
        return None
    header_value = request.headers.get("X-Request-Id")
    if not header_value:
        return None
    candidate = header_value.strip()
    return candidate or None


def _telemetry_ctx(
    current_user: UserResponse | None = None,
    request: Request | None = None,
) -> EmitContext:
    request_id = _request_id_from_header(request)
    if current_user is None:
        return EmitContext(request_id=request_id) if request_id else EmitContext()
    return EmitContext.for_user(current_user.id, request_id=request_id)


def _product_meta(session: Session, product_id: int) -> tuple[str, str]:
    product = repository.get_ingredient(session, product_id)
    if product is None:
        return "unknown", "unit"
    return product.category, product.unit


@router.get("/products", response_model=list[ProductResponse])
def list_products(
    location_id: int | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    session: Session = Depends(get_db),
) -> list[ProductResponse]:
    if location_id is not None:
        try:
            country_for_location(location_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return repository.list_ingredients(
        session,
        location_id=location_id,
        include_inactive=include_inactive,
    )


@router.post("/products", response_model=ProductResponse, status_code=201)
def create_product(
    payload: ProductCreate,
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> ProductResponse:
    try:
        return repository.create_ingredient(session, payload)
    except repository.DuplicateSkuError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    location_id: int | None = Query(default=None),
    session: Session = Depends(get_db),
) -> ProductResponse:
    if location_id is not None:
        try:
            country_for_location(location_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    product = repository.get_ingredient(session, product_id, location_id=location_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    request: Request,
    location_id: int | None = Query(default=None),
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> ProductResponse:
    if location_id is not None:
        try:
            country_for_location(location_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be a JSON object",
        )

    blocked_fields = sorted(STOCK_MUTATION_FIELDS.intersection(body))
    if blocked_fields:
        field_name = blocked_fields[0]
        category, _unit = _product_meta(session, product_id)
        props: dict[str, Any] = {
            "product_id": product_id,
            "product_category": category if category != "unknown" else None,
            "location_id": location_id,
            "attempted_field": field_name,
            "attempted_value": str(body[field_name]),
            "rejection_reason": "direct_stock_mutation_forbidden",
            "http_method": "PATCH",
            "http_path": str(request.url.path),
        }
        emit_event(
            "direct_stock_edit_rejected",
            {key: value for key, value in props.items() if value is not None},
            ctx=_telemetry_ctx(current_user, request),
            session=session,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Direct stock mutation is forbidden. "
                "Use inbound or outbound orders to change stock levels."
            ),
        )

    try:
        payload = ProductUpdate.model_validate(body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    try:
        return repository.update_ingredient(
            session, product_id, payload, location_id=location_id
        )
    except repository.IngredientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/orders/inbound", response_model=InboundOrderResponse, status_code=201)
def log_inbound_order(
    payload: InboundOrderCreate,
    request: Request,
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> InboundOrderResponse:
    ctx = _telemetry_ctx(current_user, request)

    def _failed(error_code: str) -> None:
        props: dict[str, Any] = {
            "product_id": payload.ingredient_id,
            "quantity_requested": payload.quantity,
            "location_id": payload.location_id,
            "error_code": error_code,
        }
        if payload.supplier_id is not None:
            props["supplier_id"] = str(payload.supplier_id)
        emit_event(
            "inbound_order_failed",
            props,
            ctx=ctx,
            session=session,
        )

    try:
        order = repository.create_inbound_order(
            session,
            payload,
            user_uuid=str(current_user.id),
            telemetry_ctx=ctx,
        )
    except repository.IngredientNotFoundError as exc:
        _failed("product_not_found")
        raise HTTPException(status_code=404, detail=str(exc))
    except SupplierNotFoundError as exc:
        _failed("unknown_supplier")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except SupplierInactiveError as exc:
        _failed("validation_error")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except SupplierCountryMismatchError as exc:
        _failed("validation_error")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    category, unit = _product_meta(session, order.ingredient_id)
    created_props: dict[str, Any] = {
        "inbound_order_id": order.id,
        "product_id": order.ingredient_id,
        "product_category": category,
        "quantity": order.quantity,
        "supplier_id": str(order.supplier_id),
        "location_id": order.location_id,
        "created_by": str(current_user.id),
        "unit": unit,
    }
    if order.unit_cost is not None:
        created_props["unit_cost"] = order.unit_cost
    emit_event("inbound_order_created", created_props, ctx=ctx, session=session)

    maybe_emit_ingredient_price_variance(
        session,
        inbound_order_id=order.id,
        product_id=order.ingredient_id,
        product_category=category,
        supplier_id=order.supplier_id,
        location_id=order.location_id,
        quantity=order.quantity,
        unit=unit,
        new_unit_cost=order.unit_cost,
        ctx=ctx,
    )
    return order


@router.post("/orders/outbound", response_model=OutboundOrderResponse, status_code=201)
def log_outbound_order(
    payload: OutboundOrderCreate,
    request: Request,
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> OutboundOrderResponse:
    ctx = _telemetry_ctx(current_user, request)
    try:
        order = repository.create_outbound_order(
            session,
            payload,
            user_uuid=str(current_user.id),
            telemetry_ctx=ctx,
        )
    except repository.IngredientNotFoundError as exc:
        emit_event(
            "outbound_order_failed",
            {
                "product_id": payload.ingredient_id,
                "quantity_requested": payload.quantity,
                "api_reason": payload.reason,
                "location_id": payload.location_id,
                "error_code": "product_not_found",
            },
            ctx=ctx,
            session=session,
        )
        raise HTTPException(status_code=404, detail=str(exc))
    except repository.InsufficientStockError as exc:
        emit_event(
            "outbound_order_failed",
            {
                "product_id": payload.ingredient_id,
                "quantity_requested": payload.quantity,
                "quantity_available": exc.available,
                "api_reason": payload.reason,
                "location_id": payload.location_id,
                "error_code": "insufficient_stock",
            },
            ctx=ctx,
            session=session,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    category, unit = _product_meta(session, order.ingredient_id)
    base_props = {
        "outbound_order_id": order.id,
        "product_id": order.ingredient_id,
        "product_category": category,
        "quantity": order.quantity,
        "unit": unit,
        "location_id": order.location_id,
        "created_by": str(current_user.id),
    }
    if order.reason == "waste":
        emit_event(
            "stock_waste_registered",
            {**base_props, "reason": "unspecified"},
            ctx=ctx,
            session=session,
        )
    else:
        emit_event("outbound_order_created", base_props, ctx=ctx, session=session)
    return order


@router.get("/orders", response_model=OrdersListResponse)
def list_orders(session: Session = Depends(get_db)) -> OrdersListResponse:
    return repository.list_orders(session)
