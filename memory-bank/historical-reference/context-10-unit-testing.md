# CONTEXT — Unit Test Coverage for the Authentication API · Brasaland

## AI Engineering - 4Geeks Academy

> **Task:** AUTH-088 — Unit test coverage for the authentication API
> **Repository index:** `context-10-unit-testing.md`
> **Companion doc:** `TESTING.md` (repo root) — how to run the suites + case list
> **Priority:** High
> **Type:** Hardening / engineering (no new features)
> **Status:** 🟡 Planned (not yet implemented)

> **Context for the ticket:** following last week's regression, unit tests are
> required on all authentication endpoints before any further changes are
> merged. This document records the plan to be designed and implemented.

### Locked decisions

- **Scope is testing only.** No new endpoints, pages, or features; no behavioural
  changes to the auth code beyond bug fixes that a test exposes.
- **Test the logic, not the plumbing.** Every test must assert something about the
  business logic — *what the endpoint decides, not how it responds.* HTTP
  serialisation, response shape, header casing, and framework internals are not
  under test.
- **Two layers, pure-function tests first.** The centrepiece is a layer of
  pure-function unit tests (no HTTP). A second layer of endpoint tests drives
  each route via `TestClient` but asserts only on **outcomes** (a session became
  usable, a user's state changed, a revoked token stopped working).
- **pytest for the FastAPI backend, Jest for TypeScript.** `uv run pytest` and
  `jest --coverage` must both pass cleanly.
- **Jest is additive, not a replacement.** The repo standardises on Vitest
  (`npm test`); Jest is scoped to the auth utility specs so the two never
  collide. `npm test` and CI must remain untouched.
- **Coverage gate:** ≥70% on the `auth` module.
- **Bugs found by a test get fixed and documented**, not worked around.

---

## Focus

The authentication API has strong but informally-organised coverage and no
documented test plan. AUTH-088 requires every auth endpoint to carry, at
minimum, a happy-path, an edge-case, and a failure-mode test, organised per
endpoint, plus Jest coverage of the auth-related TypeScript utilities — all
documented so the suite can be run and understood by anyone on the team.

---

## Non-negotiable principles

1. Every test asserts a **decision/outcome** of the application logic.
2. No test asserts on serialisation, response envelope shape, or framework
   internals.
3. Each endpoint has **happy + edge + failure** at minimum.
4. The suites must pass cleanly and deterministically (isolated per-test DB).
5. Any bug a test reveals is fixed in the source and recorded in `TESTING.md`.
6. Existing Vitest suites and CI must keep passing unchanged.

---

## Endpoints in scope

From `auth/routes.py` (mounted at `/auth`): `login`, `register`, `refresh`,
`logout`, `logout-all`, `me`, `verify-email`, `resend-verification`,
`forgot-password`, `reset-password`. The user-management authz on `users/routes.py`
(`/users`, `/users/{id}`) is included because it is enforced by the auth layer
(`get_current_user` / `require_admin`).

---

## Planned work

### FastAPI — pure-function unit tests (no HTTP)

- `tests/test_security.py` — `auth/security.py`: password hashing
      (round-trip, wrong/empty password, salt, 72-byte bcrypt boundary), JWT
      create/decode (subject round-trip, **expired token rejected**, wrong
      secret, tampered token), reset-token `type`/`jti` claims, opaque-token
      uniqueness + hash determinism.
- `tests/test_dependencies.py` — `auth/dependencies.py`: `get_current_user`
      happy path + **401 (not 500)** for missing/non-numeric `sub`, malformed
      token, unknown user, inactive user; `require_admin` allow/deny.
- `tests/test_refresh_tokens.py` — `auth/refresh_tokens.py`: issue/rotate,
      rotated-token reuse rejected, unknown/expired rejected, **reuse revokes the
      whole family** (theft response), `revoke_all_for_user` count.
- `tests/test_token_stores.py` — `auth/verifications.py` &
      `auth/password_resets.py`: single-use + expiry of verification tokens and
      reset `jti`s; `supersede_user_tokens`.
- `tests/test_audit.py` — `auth/audit.py`: rolling-window
      `recent_request_count` (per-email scope, event-type filter, window edges).

### FastAPI — endpoint decision tests (TestClient, assert on outcomes)

- `tests/test_register.py` — `POST /auth/register`: creates a usable session;
      duplicate/normalised-email collision; 72-byte boundary; short/oversized
      password rejected; **verification-email failure does not block signup**.
- `tests/test_login.py` — `POST /auth/login`: usable session + working
      refresh; email normalisation; empty/wrong password & unknown email
      rejected; **inactive user refused despite correct password**.
- `tests/test_token.py` — `refresh`/`logout`/`logout-all`: rotation; missing
      cookie rejected; **reused refresh token rejected**; logout revokes session;
      logout-all ends every session; **refresh refused after deactivation**.
- `tests/test_verify_email.py` — `verify-email`/`resend-verification`: valid
      token flips `is_verified`; single-use; resend short-circuits when already
      verified; bogus/expired token rejected.
- `tests/test_password_reset.py` — `forgot`/`reset`: full cycle; anti-
      enumeration; supersede; rate-limit boundary; invalid/expired/replayed
      token; **wrong token `type`**; **unknown subject**; weak password; reset
      revokes all sessions; audit events recorded.
- `tests/test_users.py` — `GET /auth/me` (no password hash leaked) + authz:
      self-update allowed, cross-user update forbidden, non-admin list forbidden,
      protected route requires auth.

### FastAPI — fixtures

- Add a `db` fixture to `tests/conftest.py` (throwaway TinyDB, no app/HTTP)
      for the pure-function tests; reuse the existing `anon_client` /
      `auth_client` fixtures for the endpoint layer.
- Retire the consolidated `tests/test_auth.py` once its cases are distributed
      across the per-endpoint modules.

### TypeScript — Jest

- `jest.config.ts` (repo root): `ts-jest` transform with an inline tsconfig,
      `node` environment, scoped to `jest-tests/*.auth.test.ts`, coverage limited
      to the three auth utility files.
- `jest-tests/auth-config.auth.test.ts` — `isPublicPath`: public routes +
      nested paths resolve public; gated routes and **look-alike prefixes**
      (`/loginx`, `/registered`) are not public.
- `jest-tests/api-error.auth.test.ts` — `formatApiError` / `parseFieldErrors`:
      string + array detail formatting, default substitution, field-keying,
      first-wins dedupe; safe fallback for non-JSON/empty bodies.
- `jest-tests/auth-storage.auth.test.ts` — token storage: set→get→clear
      round-trip (stubbed `localStorage`); SSR (`window` undefined) returns
      `null` / no-ops without throwing.
- Add `test:jest` and `test:jest:coverage` scripts; leave `npm test`
      (Vitest) and CI unchanged.
- Update `.gitignore` to exclude coverage artifacts (`coverage/`,
      `.coverage`, `.pytest_cache/`).

### FastAPI — bug-hunting tests (security & authorization)

> Added after the core suite to actively probe for broken-access-control and
> token-misuse bugs on the auth-enforced routes — the regression class this
> ticket exists to prevent. Several of these revealed real bugs (see
> `TESTING.md` → "Bugs found & fixed").

- `tests/test_authorization.py`:
  - **Privilege escalation** — a non-admin must not grant themselves `is_admin`
    (or flip `is_active`) via a self-`PUT /users/{id}`.
  - **Broken object-level authorization** — authentication alone must not permit
    `DELETE /users/{id}` of an arbitrary account (admin-or-self only).
  - **Token-type confusion** — a password-reset JWT (same secret, carries
    `type`) must not authenticate as a bearer/access token at `/auth/me`.
  - **Algorithm confusion** — a forged `alg: none` token must be rejected.
- `tests/test_register.py` — extra privileged fields in the register body
      (`is_admin`, `is_verified`) must be ignored (no mass-assignment).
- `tests/test_dependencies.py` — a validly-signed token with **no `sub`** and
      a **typed (reset) token** are both rejected by `get_current_user`.
- Defensive robustness — corrupt stored timestamps (`expires_at` /
      `created_at`) are treated as expired/skipped, never a `500`
      (`test_token_stores.py`, `test_audit.py`); the `forgot-password` audit row
      captures the first hop of `X-Forwarded-For` (`test_password_reset.py`).

---

## Key design decisions & deviations

- **TestClient is allowed at the endpoint layer** because the ticket's rule is an
  *assertion-discipline* rule, not a ban on the client. Every endpoint test
  should pair a status (read as a decision) with a state assertion where one
  exists (e.g. after logout, the old refresh token genuinely fails a real
  `/refresh`).
- **The pure-function layer carries the "real" logic tests** and most of the
  coverage, directly answering the brief's example questions.
- **TS has no token/hashing helpers** — token minting, validation, and password
  hashing live only in the Python backend (`auth/security.py`). Jest therefore
  covers the auth-related utilities that actually exist in TypeScript, and the
  token/hashing logic is covered by `tests/test_security.py`. This must be
  documented explicitly in `TESTING.md` rather than asserting against code that
  does not exist.
- **Jest specs live in top-level `jest-tests/`** (not in the backoffice tree and
  not under `src/`/`tests/`) so they are invisible to Vitest and to the Next.js /
  `tsc` build, avoiding runner collisions and build-time type errors on Jest
  globals.

---

## Verification (acceptance)

- **Backend:** `cd services/api && uv run pytest --cov=auth --cov-report=term-missing`
  — all green, ≥70% coverage on `auth`.
- **Frontend:** `npm run test:jest:coverage` (from repo root) — all green.
- **No regressions:** `npm test` (Vitest) and `npm run typecheck` stay green.
- **Bugs:** any bug a test reveals is fixed in source and recorded under
  "Bugs found & fixed" in `TESTING.md`.

---

## Deliverables

- `TESTING.md` (repo root) — run instructions, per-endpoint case list (written
  before the tests), deviation rationale, results, and the bugs found & fixed.
- `services/api/tests/` — 5 pure-function modules + 6 endpoint modules + 1
  security/authorization module (`test_authorization.py`) + `db` fixture.
- `jest.config.ts` + `jest-tests/` — 3 auth utility specs; `test:jest` scripts.
- This context document.

---

## Out of scope (explicit)

No new endpoints/pages/features, no styling or data-model changes, no dependency
bumps unrelated to testing, no changes to `npm test` or CI, and no refactors of
the auth source beyond what a failing test requires.
