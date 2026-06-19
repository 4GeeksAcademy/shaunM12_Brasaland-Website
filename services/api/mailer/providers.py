"""Transactional email backends, selected via ``config.EMAIL_PROVIDER``.

- ``console`` (default): logs/prints the message — used in dev and tests so the
  flow works with zero deliverability setup.
- ``resend`` / ``sendgrid``: deliver over HTTP using ``httpx``. API keys come
  from the environment (``RESEND_API_KEY`` / ``SENDGRID_API_KEY``) and are never
  hardcoded.

Resend's onboarding sender works without a verified domain but, on a free
account, only delivers to the Resend account owner's address until a domain is
verified. SendGrid's trial/single-sender has similar limits.
"""

from __future__ import annotations

import logging

import httpx

import config

logger = logging.getLogger("brasaland.mailer")

_RESEND_ENDPOINT = "https://api.resend.com/emails"
_SENDGRID_ENDPOINT = "https://api.sendgrid.com/v3/mail/send"
_TIMEOUT = 10.0


def _send_console(to: str, subject: str, text: str, html: str | None) -> None:
    message = (
        "\n=== [DEV EMAIL — not actually sent] ===\n"
        f"To: {to}\n"
        f"Subject: {subject}\n\n"
        f"{text}\n"
        "=======================================\n"
    )
    logger.info("Outgoing email to %s: %s", to, subject)
    print(message)


def _send_resend(to: str, subject: str, text: str, html: str | None) -> None:
    if not config.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not set")
    response = httpx.post(
        _RESEND_ENDPOINT,
        headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
        json={
            "from": config.EMAIL_FROM,
            "to": [to],
            "subject": subject,
            "html": html or text,
            "text": text,
        },
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    logger.info("Sent email via Resend to %s: %s", to, subject)


def _send_sendgrid(to: str, subject: str, text: str, html: str | None) -> None:
    if not config.SENDGRID_API_KEY:
        raise RuntimeError("SENDGRID_API_KEY is not set")
    content = [{"type": "text/plain", "value": text}]
    if html:
        content.append({"type": "text/html", "value": html})
    response = httpx.post(
        _SENDGRID_ENDPOINT,
        headers={
            "Authorization": f"Bearer {config.SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": config.EMAIL_FROM},
            "subject": subject,
            "content": content,
        },
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    logger.info("Sent email via SendGrid to %s: %s", to, subject)


def send(to: str, subject: str, text: str, html: str | None = None) -> None:
    """Dispatch an email through the configured provider."""
    provider = config.EMAIL_PROVIDER
    if provider == "resend":
        _send_resend(to, subject, text, html)
    elif provider == "sendgrid":
        _send_sendgrid(to, subject, text, html)
    else:
        _send_console(to, subject, text, html)


__all__ = ["send"]
