"""In-process throttle helpers for telemetry emission."""

from __future__ import annotations

import time

_LOGIN_FAILED_LAST_EMIT: dict[str, float] = {}
_LOGIN_FAILED_WINDOW_SECONDS = 60.0


def should_emit_login_failed(source_ip_hash: str) -> bool:
    """Allow at most one login-failure telemetry event per IP hash per minute."""
    now = time.monotonic()
    last = _LOGIN_FAILED_LAST_EMIT.get(source_ip_hash)
    if last is not None and now - last < _LOGIN_FAILED_WINDOW_SECONDS:
        return False
    _LOGIN_FAILED_LAST_EMIT[source_ip_hash] = now
    return True
