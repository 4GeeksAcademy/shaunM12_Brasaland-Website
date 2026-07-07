"""Request-scoped identifiers passed into telemetry emitters."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from .constants import ANONYMOUS_USER_ID


@dataclass(frozen=True)
class EmitContext:
    user_id: str = ANONYMOUS_USER_ID
    session_id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}")
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")

    @classmethod
    def for_user(cls, user_id: str | int | None) -> EmitContext:
        if user_id is None:
            return cls()
        return cls(user_id=str(user_id))
