"""FastAPI routes for ingredient inventory (Supabase)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from auth.dependencies import get_current_user
from database import get_db
from users.models import UserResponse
from . import repository
from .schemas import (
    InboundOrderCreate,
    InboundOrderResponse,
    OrdersListResponse,
    OutboundOrderCreate,
    OutboundOrderResponse,
    ProductCreate,
    ProductResponse,
)

router = APIRouter(tags=["inventory"])


@router.get("/products", response_model=list[ProductResponse])
def list_products(session: Session = Depends(get_db)) -> list[ProductResponse]:
    return repository.list_ingredients(session)


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
    session: Session = Depends(get_db),
) -> ProductResponse:
    product = repository.get_ingredient(session, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


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
