"""When to fire the nightly job (America/Bogota 02:00)."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")


def seconds_until_next_run(now: datetime | None = None) -> float:
    """Seconds until the next ``0 2 * * *`` tick in America/Bogota."""
    current = now or datetime.now(BOGOTA)
    if current.tzinfo is None:
        current = current.replace(tzinfo=BOGOTA)
    else:
        current = current.astimezone(BOGOTA)

    target = current.replace(hour=2, minute=0, second=0, microsecond=0)
    if current >= target:
        target = target + timedelta(days=1)
    return max(1.0, (target - current).total_seconds())
