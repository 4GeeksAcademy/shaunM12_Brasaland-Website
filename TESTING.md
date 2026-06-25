# TESTING — Authentication test suite (AUTH-088)

This document explains how to run the authentication test suites, what each
suite covers, and the reasoning behind the cases that were chosen. It is the
deliverable companion to ticket **AUTH-088 — Unit test coverage for the
authentication API**.

The guiding rule from the ticket is followed throughout:

> Every test asserts something about the **business logic of the application —
> what the endpoint decides, not how it responds.** HTTP serialisation and
> framework internals are not under test.

Two layers of tests implement that rule:

1. **Pure-function unit tests** (no HTTP at all) — import the auth functions
   directly and assert on their decisions. This is the centrepiece of the suite
   and where the example questions from the brief are answered (does a token get
   generated correctly? is an expired token rejected? what happens when the
   password is empty / too long?).
2. **Endpoint decision tests** — drive each route with FastAPI's `TestClient`
   but assert on the *outcome of the decision* (a session became usable, a
   user's state changed, a revoked token stopped working), never on JSON field
   names, header casing, or response shape for its own sake.

---

## How to run

### FastAPI / pytest

From the API project root:

```bash
cd services/api
uv sync                 # one-time: install deps (incl. pytest, pytest-cov)
uv run pytest           # run the whole suite
```

With coverage on the authentication module (the ticket's ≥70% gate):

```bash
cd services/api
uv run pytest --cov=auth --cov-report=term-missing
```

Run a single endpoint's module:

```bash
uv run pytest tests/test_login.py -v
```

### TypeScript / Jest

From the repository root (Jest is installed in the root `devDependencies`):

```bash
npm run test:jest               # run the auth utility specs
npm run test:jest:coverage      # same, with a coverage report
```

Jest is **scoped** to the authentication utility specs (`jest-tests/*.auth.test.ts`)
so it does not collide with the repository's existing Vitest suites. `npm test`
remains Vitest and is untouched. The specs live in the top-level `jest-tests/`
directory (outside `src/`, `tests/`, and the backoffice tree) so they are picked
up by neither Vitest nor the Next.js/`tsc` build.

---

## FastAPI suite — what each module covers

### Pure-function unit tests (no HTTP)

| Module | Unit under test | Focus |
| --- | --- | --- |
| `tests/test_security.py` | `auth/security.py` | password hashing, JWT create/decode, opaque tokens |
| `tests/test_dependencies.py` | `auth/dependencies.py` | `get_current_user`, `require_admin` resolution & rejection |
| `tests/test_refresh_tokens.py` | `auth/refresh_tokens.py` | issue / rotate / reuse-detection / revoke |
| `tests/test_token_stores.py` | `auth/verifications.py`, `auth/password_resets.py` | single-use + expiry of opaque/JWT-jti tokens |
| `tests/test_audit.py` | `auth/audit.py` | rolling-window reset-request counting |

### Endpoint decision tests (TestClient, asserting on outcomes)

| Module | Endpoint(s) | 
| --- | --- |
| `tests/test_register.py` | `POST /auth/register` |
| `tests/test_login.py` | `POST /auth/login` |
| `tests/test_token.py` | `POST /auth/refresh`, `/auth/logout`, `/auth/logout-all` |
| `tests/test_verify_email.py` | `POST /auth/verify-email`, `/auth/resend-verification` |
| `tests/test_password_reset.py` | `POST /auth/forgot-password`, `/auth/reset-password` |
| `tests/test_users.py` | `GET /auth/me`, `/users`, `/users/{id}` (authz decisions) |

### Security & authorization (bug-hunting)

| Module | Focus |
| --- | --- |
| `tests/test_authorization.py` | privilege escalation, broken object-level authorization, token-type & algorithm confusion |

---

## Cases covered (planned before the tests were written)

Each endpoint has, at minimum, a happy path, an edge case, and a failure mode,
per the ticket. The reasoning for each is given.

### `POST /auth/register`
- **Happy** — valid email + password creates the user and mints a working
  session (the returned access token authenticates `/auth/me`).
- **Edge** — duplicate email is rejected; a password at the 72-byte bcrypt
  boundary is accepted; an optional `name` is stored.
- **Failure** — password shorter than 8 chars is rejected by validation; a
  failing verification-email provider does **not** block signup (the account is
  still created and a session returned). *Why:* email delivery is best-effort and
  must never lose a registration.

### `POST /auth/login`
- **Happy** — correct credentials establish a usable session.
- **Edge** — empty password is rejected (no session); email is matched after
  normalisation (case/whitespace).
- **Failure** — wrong password and unknown email are both rejected;
  a **deactivated user is refused** even with the correct password. *Why:* the
  inactive-user branch is a real security decision that was previously untested.

### `POST /auth/refresh` / `logout` / `logout-all`
- **Happy** — a valid refresh cookie rotates into a new, usable access token.
- **Edge** — a missing refresh cookie is rejected; `logout` with no cookie is a
  successful no-op.
- **Failure** — a refresh token reused after rotation is rejected (and the whole
  token *family* is revoked — theft response); `logout` revokes the token so it
  can no longer refresh; `logout-all` kills every session for the user.

### `POST /auth/verify-email` / `resend-verification`
- **Happy** — a valid token flips the user's `is_verified` flag to `True`.
- **Edge** — `resend-verification` short-circuits when the user is already
  verified (no new token issued).
- **Failure** — a bogus token and an expired token are both rejected; a token
  cannot be consumed twice.

### `POST /auth/forgot-password` / `reset-password`
- **Happy** — full forgot→reset cycle: the new password works and the old one
  stops working.
- **Edge** — identical response body for known vs unknown email
  (anti-enumeration); requesting a new link supersedes the previous one; the
  hourly rate limit boundary (N allowed, N+1 blocked).
- **Failure** — invalid JWT, expired token, wrong token `type`, non-existent
  `sub`, single-use replay, and weak new password are all rejected. A reset
  revokes all of the user's existing sessions. *Why:* a password reset is a
  security event; lingering sessions would defeat it.

### `GET /auth/me` & user-management authz
- **Happy** — a valid bearer returns the current user, and `hashed_password` is
  never present in the result.
- **Edge** — a user may update their own record; an admin may update others.
- **Failure** — no/expired/malformed token is rejected; a non-admin is forbidden
  from the admin-only user list; a user cannot modify another user's record.

### Pure-function logic (the direct answers to the brief's questions)
- **Token generation correct** — `create_access_token(sub)` round-trips through
  `decode_access_token` with the right `sub`.
- **Expired token rejected** — a token minted with a negative lifetime raises
  `JWTError` on decode; a token signed with the wrong secret is rejected.
- **Password hashing** — `hash_password` never returns the plaintext; the right
  password verifies and the wrong one does not; behaviour at the 72-byte bcrypt
  boundary is documented.
- **Empty / malformed inputs** — `get_current_user` raises `401` for a missing
  `sub`, a non-numeric `sub`, an unknown user, and an inactive user, rather than
  leaking a `500`.
- **Single-use & expiry** — verification, reset-jti, and refresh tokens each
  reject reuse and expiry at the store level.

### Security & authorization (bug-hunting — several caught real bugs)
- **Privilege escalation** — a non-admin must not grant themselves `is_admin`
  (or flip `is_active`) via a self-`PUT /users/{id}`.
- **Broken object-level authorization** — authentication alone must not permit
  deleting an arbitrary account (`DELETE /users/{id}` is admin-or-self only).
- **Token-type confusion** — a password-reset JWT (signed with the same secret)
  must not authenticate as an access token at `/auth/me`.
- **Algorithm confusion** — a forged `alg: none` token is rejected.
- **Mass-assignment** — privileged fields in the register body (`is_admin`,
  `is_verified`) are ignored.
- **No-`sub` token** — a validly-signed token with no subject is rejected.
- **Defensive robustness** — corrupt stored timestamps are treated as
  expired/skipped (never a `500`); the `forgot-password` audit row captures the
  first hop of `X-Forwarded-For`.

---

## TypeScript / Jest suite — what it covers

> **Deviation & rationale (read this).** The ticket names *"token generation,
> validation, password hashing helpers"* for the Jest suite. Those concerns live
> **only in the Python backend** (`auth/security.py`) — the TypeScript code is a
> browser client and contains no token minting or password hashing. Jest
> therefore covers the auth-related **utility functions that genuinely exist in
> TypeScript**, and the token/hashing logic is fully covered by
> `tests/test_security.py` on the Python side. This keeps every test meaningful
> rather than asserting against code that does not exist.

All specs live in `jest-tests/`:

| Spec | Unit under test | Happy | Failure |
| --- | --- | --- | --- |
| `jest-tests/auth-config.auth.test.ts` | `isPublicPath` | public routes (`/login`, `/reset-password/x`) resolve as public | gated routes and look-alikes (`/dashboard`, `/loginx`) are **not** public |
| `jest-tests/api-error.auth.test.ts` | `formatApiError`, `parseFieldErrors` | string `detail` and validation arrays are formatted; field errors keyed by `loc` | non-JSON / empty bodies fall back to a safe message |
| `jest-tests/auth-storage.auth.test.ts` | `getAccessToken` / `setAccessToken` / `clearAccessToken` | set→get→clear round-trips against `localStorage` | server-side (`window` undefined) returns `null` / no-ops |

---

## Current results

| Suite | Command | Result |
| --- | --- | --- |
| FastAPI | `uv run pytest --cov=auth` | **115 passed**, **98% coverage** on the `auth` module (gate is 70%) |
| TypeScript | `npm run test:jest:coverage` | **20 passed**, **100%** statements/functions/lines on the three auth utilities |

Per-file `auth` coverage (pytest): `security.py`, `models.py`, `audit.py`,
`dependencies.py`, `password_resets.py`, `verifications.py` all 100%;
`refresh_tokens.py` 97%; `routes.py` 96%.

## Bugs found & fixed

The bug-hunting tests in `tests/test_authorization.py` surfaced **three real
broken-access-control / token-misuse bugs** in the auth-enforced routes. Each was
fixed and is now locked in by a passing test.

### 1. Privilege escalation via self-update (HIGH)
- **Test:** `test_user_cannot_escalate_self_to_admin` (and the `is_active`
  variant).
- **Root cause:** `PUT /users/{id}` let a user edit their own record, and
  `UserUpdate` includes `is_admin` / `is_active`, which were applied unchecked —
  so any user could `PUT /users/{own_id}` with `{"is_admin": true}` and become
  an admin.
- **Fix:** `users/routes.py::update_user_by_id` now returns `403` if a non-admin
  attempts to change `is_admin` or `is_active` (on any record, including their
  own). Ordinary self-service fields (name, email, password) are unaffected.

### 2. Broken object-level authorization on delete (HIGH)
- **Test:** `test_non_admin_cannot_delete_another_user`.
- **Root cause:** `DELETE /users/{id}` required only authentication — any
  logged-in user could delete any account by id.
- **Fix:** `users/routes.py::remove_user` now requires the caller to be an admin
  or the account owner; otherwise `403`.

### 3. Token-type confusion (MEDIUM)
- **Test:** `test_password_reset_token_cannot_authenticate` (plus the
  dependency-level `test_typed_token_is_rejected_as_access_token`).
- **Root cause:** `get_current_user` validated only signature + expiry. Because
  password-reset JWTs are signed with the same secret and carry a `sub`, a reset
  token could be presented as a bearer token to authenticate.
- **Fix:** `auth/dependencies.py::get_current_user` now rejects any token that
  carries a `type` claim (reset tokens do; access tokens do not).

> The `alg: none` forgery test passed against the original code — python-jose is
> already pinned to `algorithms=["HS256"]`, so no fix was needed there; the test
> locks that protection in.
