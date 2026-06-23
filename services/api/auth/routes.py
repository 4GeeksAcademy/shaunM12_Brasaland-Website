"""Authentication routes: login, register, refresh, logout, email verification."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

import config
from users.models import UserResponse
from users.repository import (
    EmailAlreadyExistsError,
    create_user,
    get_user_record,
    get_user_record_by_email,
    mark_verified,
    set_password,
)
from . import audit, password_resets, refresh_tokens, verifications
from .dependencies import get_current_user
from .models import (
    ForgotPasswordRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from .security import (
    JWTError,
    PASSWORD_RESET_TOKEN_TYPE,
    create_access_token,
    decode_password_reset_token,
    verify_password,
)
from mailer import send_password_reset_email, send_verification_email

router = APIRouter(tags=["auth"])


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=config.REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        max_age=config.REFRESH_TOKEN_EXPIRES_DAYS * 24 * 60 * 60,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=config.REFRESH_COOKIE_NAME,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def _issue_session(response: Response, user_id: int) -> TokenResponse:
    """Mint an access token and set a fresh refresh-token cookie."""
    raw_refresh = refresh_tokens.issue_refresh_token(user_id)
    _set_refresh_cookie(response, raw_refresh)
    return TokenResponse(access_token=create_access_token(user_id))


@router.post("/login", response_model=TokenResponse)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    # OAuth2PasswordRequestForm carries the email in its `username` field.
    user = get_user_record_by_email(form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _issue_session(response, user.id)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, response: Response) -> TokenResponse:
    try:
        user = create_user(payload)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Fire off a (stubbed) verification email; failures must not block signup.
    try:
        raw_token = verifications.issue_verification_token(user.id)
        send_verification_email(user.email, raw_token)
    except Exception:  # pragma: no cover - defensive; dev stub never raises
        pass

    return _issue_session(response, user.id)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=config.REFRESH_COOKIE_NAME),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    rotated = refresh_tokens.rotate_refresh_token(refresh_token)
    if rotated is None:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    new_raw, user_id = rotated

    # Reject refresh for users that were deactivated after issuing the token.
    user = get_user_record(user_id)
    if user is None or not user.is_active:
        refresh_tokens.revoke_refresh_token(new_raw)
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )

    _set_refresh_cookie(response, new_raw)
    return TokenResponse(access_token=create_access_token(user_id))


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=config.REFRESH_COOKIE_NAME),
) -> MessageResponse:
    if refresh_token:
        refresh_tokens.revoke_refresh_token(refresh_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all(
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
) -> MessageResponse:
    refresh_tokens.revoke_all_for_user(current_user.id)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out from all sessions")


@router.get("/me", response_model=UserResponse)
def read_me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(payload: VerifyEmailRequest) -> MessageResponse:
    user_id = verifications.consume_verification_token(payload.token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )
    mark_verified(user_id)
    return MessageResponse(message="Email verified")


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    current_user: UserResponse = Depends(get_current_user),
) -> MessageResponse:
    if current_user.is_verified:
        return MessageResponse(message="Email already verified")
    raw_token = verifications.issue_verification_token(current_user.id)
    send_verification_email(current_user.email, raw_token)
    return MessageResponse(message="Verification email sent")


def _client_ip(request: Request) -> str:
    """Best-effort client IP, honouring a proxy's X-Forwarded-For first hop."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Generic confirmation copy: identical regardless of whether the email exists,
# to prevent account enumeration.
_RESET_REQUESTED_MESSAGE = "If that address is registered, you'll receive a link shortly."


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest, request: Request
) -> MessageResponse:
    email = payload.email.strip().lower()
    ip = _client_ip(request)

    # Rate limit per submitted email (not per existence) to curb abuse while
    # leaking as little as possible about which addresses are registered.
    if audit.recent_request_count(email) >= config.RESET_REQUESTS_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many reset requests. Please try again later.",
        )

    user = get_user_record_by_email(email)
    audit.record_event(
        audit.REQUESTED, email, user.id if user is not None else None, ip
    )

    if user is not None:
        # A provider failure must never change the response (anti-enumeration).
        try:
            password_resets.supersede_user_tokens(user.id)
            token = password_resets.issue_reset_token(user.id)
            send_password_reset_email(user.email, token)
        except Exception:  # pragma: no cover - defensive; console stub never raises
            pass

    return MessageResponse(message=_RESET_REQUESTED_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest, request: Request
) -> MessageResponse:
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset token",
    )

    try:
        claims = decode_password_reset_token(payload.token)
    except JWTError:
        raise invalid

    if claims.get("type") != PASSWORD_RESET_TOKEN_TYPE:
        raise invalid
    subject = claims.get("sub")
    jti = claims.get("jti")
    if subject is None or jti is None:
        raise invalid
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise invalid

    user = get_user_record(user_id)
    if user is None:
        raise invalid

    # Single-use: consuming the jti flips its stored `used` flag.
    if not password_resets.consume_reset_token(jti):
        raise invalid

    set_password(user_id, payload.new_password)
    # A reset is a security event: drop every existing session.
    refresh_tokens.revoke_all_for_user(user_id)
    audit.record_event(audit.COMPLETED, user.email, user_id, _client_ip(request))

    return MessageResponse(message="Password updated. You can now sign in.")
