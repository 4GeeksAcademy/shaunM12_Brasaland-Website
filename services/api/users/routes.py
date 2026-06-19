"""FastAPI routes for user management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from auth.dependencies import get_current_user, require_admin
from .models import UserCreate, UserResponse, UserUpdate
from .repository import (
    EmailAlreadyExistsError,
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)

router = APIRouter(tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
def register_user(payload: UserCreate) -> UserResponse:
    try:
        return create_user(payload)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[UserResponse])
def get_users(_: UserResponse = Depends(require_admin)) -> list[UserResponse]:
    return list_users()


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    _: UserResponse = Depends(get_current_user),
) -> UserResponse:
    user = get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user_by_id(
    user_id: int,
    payload: UserUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to modify another user",
        )
    try:
        user = update_user(user_id, payload)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=204)
def remove_user(
    user_id: int,
    _: UserResponse = Depends(get_current_user),
) -> None:
    if not delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
