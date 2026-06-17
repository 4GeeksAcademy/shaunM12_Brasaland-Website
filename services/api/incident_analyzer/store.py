from __future__ import annotations

from .schemas import AnalysisResult

_last_result: AnalysisResult | None = None


def save_result(result: AnalysisResult) -> None:
    global _last_result
    _last_result = result


def get_result() -> AnalysisResult | None:
    return _last_result
