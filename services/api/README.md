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

## Setup

Using **uv** (recommended for seeding):

```bash
cd services/api
uv sync
uv run seed
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

Or from the repo root:

```bash
npm run api:sync
npm run api:seed
```

Using **pip** (legacy):

```bash
pip install -r services/api/requirements.txt
```

## Run

```bash
npm run api:dev
```

Seed suppliers manually (skips duplicates):

```bash
cd services/api && uv run seed
```

Or:

```bash
npm run api:seed
```

On first API startup, suppliers are auto-seeded when the database is empty.

## Authentication

JWT bearer auth. All supplier, incident, and (non-registration) user routes
require a valid token; only `GET /api/health` and the public auth routes are open.

Mounted at `/auth` (per the AUTH-01 spec):

- `POST /auth/register` — JSON `{email, password}`, creates a user and returns a token
- `POST /auth/login` — form-encoded (`username` = email, `password`), returns a token
- `GET /auth/me` — current user's profile (requires token)

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
cd services/api && uv run pytest -q
```

Or from the repo root: `npm run api:test`.
