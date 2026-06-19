"""Centralised application settings for the Brasaland API.

Loads environment variables from ``services/api/.env`` (if present) and exposes
the JWT/auth configuration used by the authentication layer.

Fails closed: importing this module raises if ``JWT_SECRET_KEY`` is missing, so
the API can never run with an insecure hardcoded default secret.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load services/api/.env when present. Real environment variables always win,
# so this is a no-op in deployments that inject config another way.
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not set. Copy services/api/.env.example to "
        "services/api/.env and provide a long random secret. The API refuses to "
        "start without a signing secret."
    )

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRES_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "30"))
