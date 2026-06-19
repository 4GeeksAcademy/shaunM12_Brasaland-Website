# CONTEXT — Authentication & Route Restriction · Brasaland

## AI Engineering - 4Geeks Academy

> **Task:** AUTH-01 — Implement authentication and route protection
> **Repository index:** `context-7-authentication-and-route-restriction.md`
> **Type:** Security hardening (not a user-facing feature)
> **Status:** ✅ Implemented (see "Locked decisions" below)

### Locked decisions (as implemented)

- **#4 Login shape:** `POST /auth/login` uses `OAuth2PasswordRequestForm`
  (form-encoded; the email goes in the `username` field) so Swagger's "Authorize"
  works out of the box. `POST /auth/register` stays JSON.
- **Route mounting:** each route is mounted **once** — auth under `/auth`, users
  under `/users` (per spec), suppliers under `/api/suppliers` (frontend proxy).
  The earlier dual-prefix mounting was removed to de-duplicate `/docs`.
- **#6 Route protection scope:** **all** `/suppliers` routes (reads included, since
  they expose `contact_email`/`notes`) and **all** incident routes are protected.
  Only `/api/health` and the public auth/register routes are open.
- **Registration:** fully public (`POST /users` and `POST /auth/register`).
- **`is_admin`:** on the user model; `PUT /users/{id}` requires owner or admin.
- **`sub`:** stored as a string, parsed back to `int` in `get_current_user`.
- **Password policy:** min 8 chars, max 72 bytes (bcrypt's effective limit).
- **Tests:** local source is made authoritative via `[tool.pytest.ini_options]`
  `pythonpath=["."]`; shared fixtures live in `tests/conftest.py`.

### Focus

Add a stateless JWT authentication layer to the Brasaland API and restrict every
route that modifies or exposes sensitive data so it cannot be reached without a
valid session. This protects everything already built (suppliers, incidents) and
everything added later.

---

## Why this exists

The API currently has **no authentication**. Anyone who can reach the backoffice
or the API can read, modify, or delete suppliers and run incident analysis. Before
the platform moves to its next phase, access must be gated behind a verified
identity.

> **Expected side effect:** Once routes are protected, some frontend calls will
> start returning `401` until the frontend is updated to send the token. This is
> acceptable for this task — the goal is securing the API first. Frontend token
> wiring is follow-up work.

---

## Hard constraints

- **Stateless JWT only.** No session storage, no cookies. Identity travels in the
  `Authorization: Bearer <token>` header on every request.
- **Never store plaintext passwords.** Use `passlib` with the **bcrypt** scheme for
  hashing and verification. **`bcrypt` is pinned to `>=4.0,<4.1`** — `passlib 1.7.x`
  is incompatible with `bcrypt 5.x` (it reads the removed `bcrypt.__about__`
  attribute and errors at hash time).
- **Secret is never hardcoded.** The JWT signing secret and expiry live in
  environment variables, loaded via `config.py` (see below). The app **fails closed**:
  if `JWT_SECRET_KEY` is missing it refuses to start rather than using a default.
- **OAuth2 + python-jose.** Use FastAPI's `OAuth2PasswordBearer` for token
  extraction and `python-jose` for signing/decoding.

---

## User model

Stored in a new TinyDB table `users` (via `database.py`).

| Field             | Type                       | Description                                  |
| ----------------- | -------------------------- | -------------------------------------------- |
| `id`              | int, system-generated      | TinyDB doc id, mirrored into the record      |
| `email`           | string, required, unique   | Login identifier; must be unique             |
| `hashed_password` | string, system-generated   | bcrypt hash — never returned in responses    |
| `is_active`       | bool, default `true`       | Disabled users cannot authenticate           |
| `is_admin`        | bool, default `false`      | Grants cross-user edit/delete (see `PUT`)    |
| `created_at`      | datetime, system-generated | Account creation timestamp (UTC ISO 8601)    |

**Response rule:** `hashed_password` must never appear in any API response. Use a
separate `UserResponse` model that omits it.

---

## Module layout

Follow the existing domain-module pattern (`suppliers/`, `incident_analyzer/`):

```
services/api/
├── config.py            # loads .env, exposes JWT_SECRET_KEY/ALGORITHM/EXPIRY (fail-closed)
├── auth/
│   ├── __init__.py
│   ├── security.py      # password hashing, JWT encode/decode (imports config.py)
│   ├── dependencies.py  # OAuth2PasswordBearer + get_current_user
│   ├── models.py        # LoginRequest, TokenResponse, RegisterRequest
│   └── routes.py        # /auth/login, /auth/register, /auth/me
├── users/
│   ├── __init__.py
│   ├── models.py        # UserCreate, UserUpdate, UserResponse, UserInDB (stored, incl. hashed_password)
│   ├── repository.py    # TinyDB CRUD + hashing on create
│   └── routes.py        # /users CRUD
└── database.py          # add get_users_table()
```

> **Already in place:** `config.py` exists and loads settings via `python-dotenv`,
> failing closed when `JWT_SECRET_KEY` is unset. `auth/security.py` should import
> its settings from `config.py` rather than re-reading the environment.

---

## Endpoints

Each route is mounted **once**. Auth routes live under `/auth` and user routes
under `/users` (per this spec). Suppliers/incidents remain under `/api/...` to
match the existing Next.js proxy. (The earlier dual-prefix mounting — both
`/api/<x>` and `/<x>` — was dropped so `/docs` lists each route a single time.)

### User management — `/users`

| Method | Path          | Auth        | Notes                                                    |
| ------ | ------------- | ----------- | -------------------------------------------------------- |
| POST   | `/users`      | **Public**  | Register a user; hashes the password before storing      |
| GET    | `/users`      | Protected   | List all users (no `hashed_password`)                    |
| GET    | `/users/{id}` | Protected   | Get a single user                                        |
| PUT    | `/users/{id}` | Protected   | Update; allowed only when `current_user.id == id` **or** `current_user.is_admin`, else `403` |
| DELETE | `/users/{id}` | Protected   | Delete a user                                            |

### Authentication — `/auth`

| Method | Path             | Auth       | Notes                                                       |
| ------ | ---------------- | ---------- | ---------------------------------------------------------- |
| POST   | `/auth/login`    | Public     | Validates email + password, returns a signed JWT           |
| POST   | `/auth/register` | Public     | Creates a user and returns a token (logged in immediately) |
| GET    | `/auth/me`       | Protected  | Returns the current authenticated user's profile           |

---

## Token & dependency

### JWT contents
- **Subject (`sub`)**: the user's `id` (at minimum).
- **`exp`**: expiry, set from `ACCESS_TOKEN_EXPIRES_MINUTES`.
- **Algorithm**: `HS256` (configurable via env if desired).

### `get_current_user` dependency
1. Extract the bearer token via `OAuth2PasswordBearer(tokenUrl="auth/login")`.
2. Decode/validate the JWT with the signing secret (catch `JWTError`).
3. Load the user from the `users` table by the `sub` id.
4. Raise `HTTPException(401)` if the token is missing, malformed, expired, the
   user doesn't exist, or `is_active` is `false`.

### Environment variables (`services/api/.env`)
| Variable                       | Example | Purpose                          |
| ------------------------------ | ------- | -------------------------------- |
| `JWT_SECRET_KEY`               | (random, long) | Signing secret — never commit |
| `ACCESS_TOKEN_EXPIRES_MINUTES` | `30`    | Token lifetime window            |
| `JWT_ALGORITHM`                | `HS256` | Signing algorithm (optional)     |

> **Status:** `services/api/.env` (gitignored) and `services/api/.env.example`
> (committed template) already exist, and `config.py` loads them via
> `python-dotenv`. `.env` and `**/.env` are git-ignored while `.env.example` is
> explicitly un-ignored. The secret is never committed.

---

## Route protection

Apply `get_current_user` as a dependency to every non-public route.

| Route                         | Public? |
| ----------------------------- | ------- |
| `POST /users` (register)      | ✅ Public |
| `POST /auth/login`            | ✅ Public |
| `POST /auth/register`         | ✅ Public |
| `GET /auth/me`                | 🔒 Protected |
| All other `/users` routes     | 🔒 Protected |
| **All** `/suppliers` routes (reads included) | 🔒 Protected |
| **All** incident routes       | 🔒 Protected |
| `GET /api/health`             | ✅ Public |

- Unauthenticated request to a protected route → **`401 Unauthorized`**.
- Authenticated user accessing a resource they don't own (e.g. editing another
  user) → **`403 Forbidden`**.

> **Supplier/incident scope:** at minimum, protect routes that **modify** data
> (POST/PUT/PATCH/DELETE) and any that expose sensitive records. Read-only health
> (`/api/health`) stays public.

---

## Testing (manual via `/docs`)

1. **Register** → `POST /auth/register` (or `POST /users`) with email + password.
2. **Login** → `POST /auth/login`, copy the returned `access_token`.
3. **Authorize** in Swagger (`/docs` → "Authorize") and call a protected route
   (e.g. `GET /users`, `GET /auth/me`) → `200`.
4. **No token** on a protected route → **`401`**.
5. **Malformed/expired token** on a protected route → **`401`**.
6. **Ownership** → user A trying to `PUT /users/{B_id}` → **`403`**.

Automated tests mirror these in `services/api/tests/test_auth.py` (hashing
round-trip, login success/failure, protected route 401, ownership 403,
duplicate-email 400). Shared fixtures in `tests/conftest.py`:
- `client` — authentication bypassed via `app.dependency_overrides`; used by the
  supplier/incident tests so they stay focused on their own behaviour.
- `anon_client` — real app, no token (for 401/registration/login flows).
- `auth_client` — real app with a bearer token for a freshly registered user.

---

## Out of scope (for this task)

- Frontend token storage and attaching `Authorization` headers (follow-up work).
- Refresh tokens, password reset, email verification.
- Role management beyond a basic `admin` distinction (if implemented, keep minimal).

---

_Internal document — 4Geeks Academy · AI Engineering Track_
