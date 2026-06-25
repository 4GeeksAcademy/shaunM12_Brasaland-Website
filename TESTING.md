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
| FastAPI | `uv run pytest --cov=auth` | **103 passed**, **96% coverage** on the `auth` module (gate is 70%) |
| TypeScript | `npm run test:jest:coverage` | **20 passed**, **100%** statements/functions/lines on the three auth utilities |

Per-file `auth` coverage (pytest): `security.py` 100%, `models.py` 100%,
`dependencies.py` 96%, `refresh_tokens.py` 97%, `password_resets.py` 95%,
`verifications.py` 94%, `routes.py` 95%, `audit.py` 92%.

## Bugs found & fixed

_None._ Every planned case — including the previously-untested security
branches (login by a deactivated user, refresh after deactivation,
reset-token `type`/subject validation, non-numeric JWT subject) — was found to
already behave correctly. The new tests lock that behaviour in against future
regressions, which is the explicit purpose of this ticket.
