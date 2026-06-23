# Brasaland API

FastAPI service for Brasaland backoffice tools: incident CSV analysis and the procurement supplier directory.

## Package layout

- `incident_analyzer/` — milestone 5 incident CSV analysis
- `suppliers/` — Milestone 09 supplier directory (Pydantic models, TinyDB repository, routes)
- `auth/` — JWT authentication (password hashing, token encode/decode, `get_current_user`)
- `users/` — user management (models, TinyDB repository, CRUD routes)
- `config.py` — loads `.env` and exposes JWT settings (fails closed if the secret is missing)
- `database.py` — TinyDB initialisation
- `seed.py` — initial supplier seed loader

This service uses **[uv](https://docs.astral.sh/uv/)**. The virtual environment lives in `services/api/.venv` and is created/managed by `uv` from `pyproject.toml`. Never commit `.venv`.

## Setup

Install dependencies (creates `services/api/.venv`):

```bash
cd services/api
uv sync
```

### Environment

Authentication needs a signing secret. Copy the template and set a strong value:

```bash
cd services/api
cp .env.example .env
# then edit .env, e.g.:
python -c "import secrets; print(secrets.token_hex(32))"
```

`.env` is gitignored; the API refuses to start if `JWT_SECRET_KEY` is unset.

#### Email (password reset & verification)

Transactional email is sent through a configurable provider. In dev the default
`EMAIL_PROVIDER=console` just logs/prints the message (including the reset link),
so the flow works with no external setup.

| Variable          | Example                 | Purpose                                        |
| ----------------- | ----------------------- | ---------------------------------------------- |
| `EMAIL_PROVIDER`  | `console`/`resend`/`sendgrid` | Selects the sender backend               |
| `EMAIL_FROM`      | `onboarding@resend.dev` | Sender address                                 |
| `RESEND_API_KEY`  | (secret)                | Required when `EMAIL_PROVIDER=resend`           |
| `SENDGRID_API_KEY`| (secret)                | Required when `EMAIL_PROVIDER=sendgrid`         |
| `PASSWORD_RESET_EXPIRES_MINUTES` | `30`     | Reset-token lifetime                           |
| `RESET_REQUESTS_PER_HOUR`        | `10`     | Reset requests per email per hour (then `429`) |

API keys are read from environment variables only and must never be committed.
With Resend's onboarding sender (`onboarding@resend.dev`) on a free account, email
is delivered only to the Resend account owner's address until a domain is verified.

Or from the repo root:

```bash
npm run api:install   # alias for: cd services/api && uv sync
```

## Run

From the repo root:

```bash
npm run api:dev       # http://127.0.0.1:8000
```

Or directly:

```bash
cd services/api
uv run uvicorn main:app --reload --port 8000
```

## Seed

On first API startup, suppliers are auto-seeded when the database is empty. To seed manually (skips duplicates):

```bash
npm run api:seed      # or: cd services/api && uv run seed
```

## Authentication

JWT bearer auth. All supplier, incident, and (non-registration) user routes
require a valid token; only `GET /api/health` and the public auth routes are open.

Mounted at `/auth` (per the AUTH-01 spec):

- `POST /auth/register` — JSON `{email, password}`, creates a user and returns a token
- `POST /auth/login` — form-encoded (`username` = email, `password`), returns a token
- `GET /auth/me` — current user's profile (requires token)
- `POST /auth/forgot-password` — JSON `{email}`; always returns `200` (never reveals
  whether the email exists); emails a reset link when the user exists. Returns `429`
  after `RESET_REQUESTS_PER_HOUR` requests for the same email within an hour.
- `POST /auth/reset-password` — JSON `{token, new_password}`; validates the signed,
  single-use reset JWT (signature + expiry + unused `jti`), updates the password, and
  revokes existing sessions. Returns `400` for an invalid/expired/used token.

User management at `/users`; `POST` is public, the rest require a token.
`PUT /users/{id}` is allowed only for the user themselves or an admin.

In Swagger (`/docs`), click **Authorize**, log in with email/password, then call
protected routes. Without a token, protected routes return `401`.

## Incident endpoints

- `POST /api/incidents/analyze` — multipart CSV upload, returns JSON summary
- `GET /api/incidents/results/export` — downloads the last analysis as `results.csv`
- `GET /api/health` — health check

## Supplier endpoints

Mounted at `/api/suppliers` (matches the Next.js proxy):

- `POST /api/suppliers` — register supplier (422 on invalid input)
- `GET /api/suppliers?country=&category=` — list with optional filters
- `GET /api/suppliers/{id}` — supplier detail (404 if missing)
- `PATCH /api/suppliers/{id}/rate` — update rate and `rate_updated_at`
- `PATCH /api/suppliers/{id}/status` — activate or suspend
- `PATCH /api/suppliers/{id}/notes` — update procurement notes
- `DELETE /api/suppliers/{id}` — remove erroneous record (404 if missing)

## Tests

```bash
npm run api:test      # or: cd services/api && uv run pytest tests/ -q
```

Or from the repo root: `npm run api:test`.