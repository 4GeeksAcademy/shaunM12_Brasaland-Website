"""TinyDB initialisation for the Brasaland API."""

from __future__ import annotations

import os
from pathlib import Path

from tinydb import TinyDB

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


def get_db() -> TinyDB:
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
    return get_db().table("suppliers")


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
