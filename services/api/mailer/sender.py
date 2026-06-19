"""Email sender.

Development stub: emails are printed to the console (and the logger) instead of
being delivered. The :func:`send_email` interface is intentionally small so a
real SMTP/provider implementation can replace the body without touching callers.
"""

from __future__ import annotations

import logging

import config

logger = logging.getLogger("brasaland.mailer")


def send_email(to: str, subject: str, body: str) -> None:
    """Deliver an email. In dev this just logs/prints it."""
    message = (
        "\n=== [DEV EMAIL — not actually sent] ===\n"
        f"To: {to}\n"
        f"Subject: {subject}\n\n"
        f"{body}\n"
        "=======================================\n"
    )
    logger.info("Outgoing email to %s: %s", to, subject)
    print(message)


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


__all__ = ["send_email", "send_verification_email"]
