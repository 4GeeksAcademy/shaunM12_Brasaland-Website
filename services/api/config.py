"""Centralised application settings for the Brasaland API.

Loads environment variables from ``services/api/.env`` (if present) and exposes
the JWT/auth configuration used by the authentication layer.

Fails closed: importing this module raises if ``JWT_SECRET_KEY`` is missing, so
the API can never run with an insecure hardcoded default secret.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load services/api/.env when present. Real environment variables always win,
# so this is a no-op in deployments that inject config another way.
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not set. Copy services/api/.env.example to "
        "services/api/.env and provide a long random secret. The API refuses to "
        "start without a signing secret."
    )

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRES_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "30"))

# Runtime environment. "development" enables dev conveniences — notably the
# console email provider echoing full message bodies (which contain reset and
# verification links/tokens) to stdout. ANY other value is treated as non-dev:
# the console provider then refuses to print tokens/links so secrets never leak
# to logs. Set APP_ENV=production in deployments (and use a real EMAIL_PROVIDER).
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_DEV = APP_ENV == "development"


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# --- Refresh tokens & auth cookie -------------------------------------------
REFRESH_TOKEN_EXPIRES_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "7"))
REFRESH_COOKIE_NAME = os.getenv("REFRESH_COOKIE_NAME", "brasaland_refresh")
# Set COOKIE_SECURE=true in production (HTTPS). Left false for local http dev.
COOKIE_SECURE = _as_bool(os.getenv("COOKIE_SECURE"), default=False)

# --- Email verification ------------------------------------------------------
EMAIL_VERIFICATION_EXPIRES_HOURS = int(
    os.getenv("EMAIL_VERIFICATION_EXPIRES_HOURS", "24")
)
# Base URL of the backoffice, used to build links in (stubbed) emails.
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")

# --- Password reset ----------------------------------------------------------
# Short-lived reset tokens: 15-60 minutes is standard.
PASSWORD_RESET_EXPIRES_MINUTES = int(os.getenv("PASSWORD_RESET_EXPIRES_MINUTES", "30"))
# Max reset requests accepted per email address per rolling hour (then 429).
RESET_REQUESTS_PER_HOUR = int(os.getenv("RESET_REQUESTS_PER_HOUR", "10"))

# --- Transactional email -----------------------------------------------------
# Provider backend: "console" (dev default, logs/prints), "resend", or "sendgrid".
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "console").strip().lower()
# Verified/onboarding sender address. Resend's onboarding sender works without a
# custom domain but only delivers to the Resend account owner's address in dev.
EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
# API keys are read from the environment only — never hardcode them.
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
