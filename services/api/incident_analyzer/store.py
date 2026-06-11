from __future__ import annotations

from typing import Any

_last_result: dict[str, Any] | None = None


def save_result(result: dict[str, Any]) -> None:
    global _last_result
    _last_result = result


def get_result() -> dict[str, Any] | None:
    return _last_result
