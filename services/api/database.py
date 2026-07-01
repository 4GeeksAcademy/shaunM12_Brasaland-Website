"""Database connections for the Brasaland API.

TinyDB (JSON files) remains the default persistence layer for suppliers, users,
and auth.  When ``DATABASE_URL`` is set (Supabase/PostgreSQL), SQLModel code can
opt in via :func:`get_engine` / :func:`get_db` without changing the TinyDB
accessors below.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, create_engine
from sqlalchemy.engine import Engine
from tinydb import TinyDB

import config

_default_data_dir = Path(__file__).resolve().parent / "data"

# Three separate stores keep concerns isolated:
#   - suppliers.json  -> supplier catalogue
#   - users.json      -> user accounts
#   - auth.json       -> auth machinery (sessions, verification, resets, audit)
DB_PATH = Path(os.getenv("SUPPLIERS_DB_PATH", _default_data_dir / "suppliers.json"))
USERS_DB_PATH = Path(os.getenv("USERS_DB_PATH", _default_data_dir / "users.json"))
AUTH_DB_PATH = Path(os.getenv("AUTH_DB_PATH", _default_data_dir / "auth.json"))
DATA_DIR = DB_PATH.parent

_db: TinyDB | None = None
_users_db: TinyDB | None = None
_auth_db: TinyDB | None = None
_engine: Engine | None = None


def _get_suppliers_tinydb() -> TinyDB:
    """TinyDB handle for the suppliers JSON store (internal)."""
    global _db
    if _db is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = TinyDB(DB_PATH)
    return _db


def get_users_db() -> TinyDB:
    global _users_db
    if _users_db is None:
        USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _users_db = TinyDB(USERS_DB_PATH)
    return _users_db


def get_auth_db() -> TinyDB:
    global _auth_db
    if _auth_db is None:
        AUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _auth_db = TinyDB(AUTH_DB_PATH)
    return _auth_db


def get_suppliers_table():
    return _get_suppliers_tinydb().table("suppliers")


def get_users_table():
    return get_users_db().table("users")


def get_refresh_tokens_table():
    return get_auth_db().table("refresh_tokens")


def get_email_verifications_table():
    return get_auth_db().table("email_verifications")


def get_password_resets_table():
    return get_auth_db().table("password_resets")


def get_auth_audit_table():
    return get_auth_db().table("auth_audit")


# --- Supabase / PostgreSQL (SQLModel) ----------------------------------------


def get_engine() -> Engine:
    """Return a lazily-created SQLAlchemy engine for ``config.DATABASE_URL``."""
    global _engine
    if _engine is None:
        if not config.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not set. Add your Supabase connection string to "
                "services/api/.env (see .env.example)."
            )
        _engine = create_engine(
            config.DATABASE_URL,
            pool_pre_ping=True,
        )
    return _engine


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield one SQLModel session per request.

    No session is stored on the module — each call opens a session from the
    shared engine and closes it when the request finishes.

    Usage::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    session = Session(get_engine())
    try:
        yield session
    finally:
        session.close()


__all__ = [
    "DATA_DIR",
    "DB_PATH",
    "USERS_DB_PATH",
    "AUTH_DB_PATH",
    "get_users_db",
    "get_auth_db",
    "get_suppliers_table",
    "get_users_table",
    "get_refresh_tokens_table",
    "get_email_verifications_table",
    "get_password_resets_table",
    "get_auth_audit_table",
    "get_engine",
    "get_db",
]
