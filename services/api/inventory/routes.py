"""FastAPI routes for ingredient inventory (Supabase)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from auth.dependencies import get_current_user
from database import get_db
from users.models import UserResponse
from . import repository
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
def update_product(
    product_id: int,
    payload: ProductUpdate,
    location_id: int | None = Query(default=None),
    session: Session = Depends(get_db),
    _: UserResponse = Depends(get_current_user),
) -> ProductResponse:
    if location_id is not None:
        try:
            country_for_location(location_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    try:
        return repository.update_ingredient(
            session, product_id, payload, location_id=location_id
        )
    except repository.IngredientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/orders/inbound", response_model=InboundOrderResponse, status_code=201)
def log_inbound_order(
    payload: InboundOrderCreate,
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> InboundOrderResponse:
    try:
        return repository.create_inbound_order(
            session, payload, user_uuid=str(current_user.id)
        )
    except repository.IngredientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/orders/outbound", response_model=OutboundOrderResponse, status_code=201)
def log_outbound_order(
    payload: OutboundOrderCreate,
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> OutboundOrderResponse:
    try:
        return repository.create_outbound_order(
            session, payload, user_uuid=str(current_user.id)
        )
    except repository.IngredientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except repository.InsufficientStockError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/orders", response_model=OrdersListResponse)
def list_orders(session: Session = Depends(get_db)) -> OrdersListResponse:
    return repository.list_orders(session)
