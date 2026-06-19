"""TinyDB initialisation for the Brasaland API."""

from __future__ import annotations

import os
from pathlib import Path

from tinydb import TinyDB

_default_data_dir = Path(__file__).resolve().parent / "data"
DB_PATH = Path(os.getenv("SUPPLIERS_DB_PATH", _default_data_dir / "suppliers.json"))
DATA_DIR = DB_PATH.parent

_db: TinyDB | None = None


def get_db() -> TinyDB:
    global _db
    if _db is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _db = TinyDB(DB_PATH)
    return _db


def get_suppliers_table():
    return get_db().table("suppliers")


def get_users_table():
    return get_db().table("users")


def get_refresh_tokens_table():
    return get_db().table("refresh_tokens")


def get_email_verifications_table():
    return get_db().table("email_verifications")
