"""Email sender.

The low-level :func:`send_email` dispatches through a configurable provider
(console stub in dev, Resend/SendGrid in production — see ``providers.py``). The
interface is intentionally small so call sites never depend on the backend.
"""

from __future__ import annotations

import logging

import config
from . import providers
from .templates import password_reset_email

logger = logging.getLogger("brasaland.mailer")


def send_email(to: str, subject: str, body: str, html: str | None = None) -> None:
    """Deliver an email via the configured provider (console-logged in dev)."""
    providers.send(to, subject, body, html)


def send_verification_email(to: str, raw_token: str) -> None:
    """Send the email-verification link for a freshly registered user."""
    link = f"{config.FRONTEND_BASE_URL}/verify-email?token={raw_token}"
    body = (
        "Welcome to Brasaland!\n\n"
        "Please confirm your email address by opening the link below:\n"
        f"{link}\n\n"
        f"This link expires in {config.EMAIL_VERIFICATION_EXPIRES_HOURS} hours."
    )
    send_email(to, "Verify your Brasaland email", body)


def send_password_reset_email(to: str, token: str) -> None:
    """Send the password-reset link (styled HTML + plain-text fallback)."""
    link = f"{config.FRONTEND_BASE_URL}/reset-password?token={token}"
    text, html = password_reset_email(link, config.PASSWORD_RESET_EXPIRES_MINUTES)
    send_email(to, "Reset your Brasaland password", text, html)


__all__ = ["send_email", "send_verification_email", "send_password_reset_email"]
