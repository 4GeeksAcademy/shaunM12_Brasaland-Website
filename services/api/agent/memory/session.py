"""Database session helper for agent memory graph nodes."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session


def memory_db_configured() -> bool:
    import config

    return bool(config.DATABASE_URL)


@contextmanager
def open_memory_session() -> Iterator[Session | None]:
    """Yield a SQLModel session when ``DATABASE_URL`` is set; otherwise None."""
    if not memory_db_configured():
        yield None
        return
    from database import get_engine

    session = Session(get_engine())
    try:
        yield session
    finally:
        session.close()
