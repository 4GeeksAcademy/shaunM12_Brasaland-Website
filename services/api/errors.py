"""Shared helpers for consistent, safe error handling across the API.

The goal (see context-9 error-handling roadmap): log full diagnostics
server-side (original exception + stack trace) while returning only a curated,
human-readable message to the client. No traceback, internal path, secret, or
raw third-party error should ever reach the response body.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger (``brasaland.<name>``) for a module/package."""
    return logging.getLogger(f"brasaland.{name}")


def safe_http_error(
    logger: logging.Logger,
    status_code: int,
    public_detail: str,
    *,
    exc: BaseException | None = None,
    log_message: str | None = None,
) -> HTTPException:
    """Log the real failure and return a client-safe ``HTTPException``.

    ``public_detail`` is the only text returned to the caller. ``exc`` (the
    original exception) and ``log_message`` stay in the server logs.
    """
    message = log_message or public_detail
    if exc is not None:
        logger.error(message, exc_info=exc)
    else:
        logger.error(message)
    return HTTPException(status_code=status_code, detail=public_detail)
