"""Authentication dependencies: bearer extraction + current-user resolution."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from users.models import UserResponse
from users.repository import get_user_record
from .security import JWTError, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise _credentials_exception
        user_id = int(subject)
    except (JWTError, ValueError):
        raise _credentials_exception

    user = get_user_record(user_id)
    if user is None:
        raise _credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserResponse.model_validate(user.model_dump())


def require_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Dependency that allows only admin users through."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
