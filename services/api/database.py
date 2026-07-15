"""Database connections for the Brasaland API.

TinyDB (JSON files) remains the default persistence layer for suppliers, users,
and auth.  When ``DATABASE_URL`` is set (Supabase/PostgreSQL), SQLModel code can
opt in via :func:`get_engine` / :func:`get_db` without changing the TinyDB
accessors below.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlmodel import Session, create_engine
from sqlalchemy.engine import Engine
from tinydb import TinyDB
from tinydb.table import Table
from tinydb.storages import JSONStorage

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

# Per-file locks serialize TinyDB IO and read-modify-write cycles across
# FastAPI's sync threadpool (prevents JSONDecodeError and lost updates).
_STORAGE_LOCKS: dict[str, threading.RLock] = {}
_STORAGE_LOCKS_GUARD = threading.Lock()


def _lock_for(path: str | Path) -> threading.RLock:
    key = str(Path(path).resolve())
    with _STORAGE_LOCKS_GUARD:
        lock = _STORAGE_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _STORAGE_LOCKS[key] = lock
        return lock


class ThreadSafeJSONStorage(JSONStorage):
    """JSONStorage that serializes read/write for concurrent request threads.

    TinyDB's default storage rewrites the whole file on each mutation. Under
    uvicorn + FastAPI threadpool workers, concurrent auth reads can observe a
    partially rewritten file and raise ``JSONDecodeError``.
    """

    def __init__(self, path: str, create_dirs: bool = False, encoding: str = "utf-8", **kwargs: Any):
        super().__init__(path, create_dirs=create_dirs, encoding=encoding, **kwargs)
        self._io_lock = _lock_for(path)

    def read(self) -> dict[str, dict[str, Any]] | None:
        with self._io_lock:
            last_error: json.JSONDecodeError | None = None
            for attempt in range(3):
                try:
                    return super().read()
                except json.JSONDecodeError as exc:
                    last_error = exc
                    if attempt < 2:
                        time.sleep(0.01 * (attempt + 1))
                        continue
            assert last_error is not None
            raise last_error

    def write(self, data: dict[str, dict[str, Any]]) -> None:
        with self._io_lock:
            super().write(data)


class LockedTable:
    """Proxy that holds the file lock for an entire TinyDB table operation.

    Storage-level locks alone are not enough: TinyDB ``insert``/``update`` do
    read → mutate → write. Without a spanning lock, concurrent writers can
    overwrite each other even when each storage call is locked.
    """

    def __init__(self, table: Table, lock: threading.RLock):
        self._table = table
        self._lock = lock

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._table, name)
        if not callable(attr):
            return attr

        def locked_call(*args: Any, **kwargs: Any) -> Any:
            with self._lock:
                return attr(*args, **kwargs)

        return locked_call


def _open_tinydb(path: Path) -> TinyDB:
    path.parent.mkdir(parents=True, exist_ok=True)
    return TinyDB(path, storage=ThreadSafeJSONStorage)


def _locked_table(db: TinyDB, table_name: str, path: Path) -> LockedTable:
    return LockedTable(db.table(table_name), _lock_for(path))


def _get_suppliers_tinydb() -> TinyDB:
    """TinyDB handle for the suppliers JSON store (internal)."""
    global _db
    if _db is None:
        _db = _open_tinydb(DB_PATH)
    return _db


def get_users_db() -> TinyDB:
    global _users_db
    if _users_db is None:
        _users_db = _open_tinydb(USERS_DB_PATH)
    return _users_db


def get_auth_db() -> TinyDB:
    global _auth_db
    if _auth_db is None:
        _auth_db = _open_tinydb(AUTH_DB_PATH)
    return _auth_db


def get_suppliers_table():
    return _locked_table(_get_suppliers_tinydb(), "suppliers", DB_PATH)


def get_users_table():
    return _locked_table(get_users_db(), "users", USERS_DB_PATH)


def get_refresh_tokens_table():
    return _locked_table(get_auth_db(), "refresh_tokens", AUTH_DB_PATH)


def get_email_verifications_table():
    return _locked_table(get_auth_db(), "email_verifications", AUTH_DB_PATH)


def get_password_resets_table():
    return _locked_table(get_auth_db(), "password_resets", AUTH_DB_PATH)


def get_auth_audit_table():
    return _locked_table(get_auth_db(), "auth_audit", AUTH_DB_PATH)


# --- Supabase / PostgreSQL (SQLModel) ----------------------------------------


def get_engine() -> Engine:
    """Return a lazily-created SQLAlchemy engine for ``config.DATABASE_URL``."""
    global _engine
    if _engine is None:
        if not config.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not set. Add your Supabase connection string to "
                ".env at the repository root (see .env.example)."
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
    "ThreadSafeJSONStorage",
    "LockedTable",
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
