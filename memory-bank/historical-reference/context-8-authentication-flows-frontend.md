# CONTEXT — Authentication Flows, Sessions & Account Management · Brasaland

## AI Engineering - 4Geeks Academy

> **Task:** AUTH-02 — Authentication flows and protected views (complete auth system)
> **Repository index:** `context-8-authentication-flows-frontend.md`
> **Type:** Feature (frontend-led, with required API extensions)
> **Status:** 🟡 Planned (not yet implemented)

### Locked decisions

- **Token transport:** access token (short-lived, 30 min) in **localStorage**, sent as
  `Authorization: Bearer <token>` on every protected call.
- **Refresh tokens:** **stored & revocable** in TinyDB; delivered to the browser in an
  **HttpOnly cookie**. Enables silent re-auth, logout, and logout-all.
- **Route protection:** real Next.js **middleware** checks the HttpOnly refresh cookie's
  presence and redirects to `/login`; a client `AuthGuard` handles `401`/refresh reactions.
- **`name` field** added to the API user model and to `PUT /users/{id}`.
- **`is_verified` field** added; email verification uses **allow-login + banner** (not a hard block).
- **Email verification** ships; email is **stubbed to the console** in dev, behind a clean
  interface so real SMTP can replace it later.
- **Role admin** UI at **`/account/users`** (admin-only); `GET /users` restricted to admins.
- **Login is form-encoded** (`username` = email, `password`); **register is JSON**.
- **Public website** (`uis/website`, Milestone 1) is entirely untouched.
- **Password reset is out of this update** (`/auth/forgot-password`, `/auth/reset-password`)
  — planned for a later update (see "Deferred").

---

## Focus

Deliver a full session lifecycle for the **backoffice**: register/login, silent token
refresh, account management (profile, change password), email verification, admin user
management, and route protection. The public website stays fully public.

---

## Why this exists

The API rejects unauthenticated requests on protected routes (`401`), but the backoffice
currently sends no token, so its calls will start failing. This task wires the frontend to
that contract and rounds the system out into a complete, resilient auth experience: sessions
survive access-token expiry, and users can verify their accounts.

---

## Current state (as found)

- **Apps:** `uis/website` (public Milestone 1) and `uis/backoffice` (App Router).
- **Backoffice routes:** `/`, `/suppliers`, `/suppliers/[id]`, `/incidents`,
  `/candidates/[id]`, `/data-processing`. All `"use client"` except `/data-processing`
  (server component, static sample data, no API call).
- **API clients:** `lib/suppliers-api.ts` & `lib/incidents-api.ts` → the Brasaland API
  (need a token); `lib/api.ts` → an external 4Geeks tracker (no token; the *route* still
  requires a session).
- **Proxy (`next.config.mjs`)** rewrites only `/api/incidents/*` and `/api/suppliers/*` to
  the API origin. No `/auth/*` or `/users/*` rewrites yet.

---

## Existing API contract (what the frontend builds against)

- `POST /auth/login` — **form-encoded** (`username` = email, `password`) → `{access_token, token_type}`.
- `POST /auth/register` — **JSON** `{email, password, name}` → token.
- `GET /auth/me` — returns the current user (`Bearer` required).
- `/users` CRUD — `POST /users` public; `GET/PUT/DELETE` protected. `PUT /users/{id}` is
  allowed only for the owner or an admin (else `403`).
- Protected calls return `401` when the token is missing, malformed, expired, or the user is
  inactive. `hashed_password` is never returned.
- Access-token expiry comes from the API's environment config (currently 30 minutes).

> The API authenticates protected calls **solely** via the `Bearer` access token. The
> refresh cookie introduced below is used only to mint new access tokens and to let
> middleware gate routes — it is never trusted for resource authorization.

---

## Hard constraints

- Access token in localStorage; `Authorization: Bearer` on every protected call.
- Refresh token only in an HttpOnly, `SameSite=Lax`, `Secure` (in prod) cookie — never in JS.
- Auth/refresh/logout calls go through the **same-origin proxy** with `credentials: "include"`.
- On `401`: attempt one silent refresh; on refresh failure → clear access token **and cookie**,
  redirect `/login`.
- On logout: revoke the refresh token server-side, clear the cookie + localStorage, redirect `/login`.
- No separate auth app; integrate into `uis/backoffice`.
- Public website untouched.
- Never log tokens; never expose `hashed_password`.

---

## Architecture & module layout

### API (`services/api/`)

```
auth/
├── models.py        # + RefreshResponse, VerifyEmailRequest, ResendVerificationRequest
├── security.py      # + refresh-token create/hash/verify, verification-token helpers
├── routes.py        # + /auth/refresh, /auth/logout, /auth/logout-all, /auth/verify-email,
│                    #   /auth/resend-verification
└── dependencies.py  # + require_admin dependency
users/
├── models.py        # + name, is_verified on the user models (with defaults — see below)
└── repository.py    # + name/is_verified persistence; admin-only listing helper
email/               # NEW
├── __init__.py
└── sender.py        # console/stub sender behind a swappable interface
database.py          # + get_refresh_tokens_table(), get_email_verifications_table()
config.py            # + REFRESH_TOKEN_EXPIRES_DAYS, cookie name/secure, FRONTEND_BASE_URL
```

### Backoffice (`uis/backoffice/`)

```
middleware.ts                         # NEW — refresh-cookie presence → redirect /login
next.config.mjs                       # CHANGE — add /auth/* and /users/* rewrites
lib/
├── auth-storage.ts                   # NEW — access-token get/set/clear (localStorage)
├── auth-api.ts                       # NEW — login, register, refresh, logout,
│                                     #        verifyEmail, resendVerification, getMe
├── users-api.ts                      # NEW — list/get/update/delete users
├── http.ts                           # NEW — authorizedFetch: Bearer + single-flight
│                                     #        401→refresh→retry
├── suppliers-api.ts / incidents-api.ts  # CHANGE — go through authorizedFetch
context/AuthProvider.tsx              # NEW — session/user state, logout(); inits after mount
components/auth/
├── AuthGuard.tsx                     # NEW — client guard + 401 reaction
├── AdminGuard.tsx                    # NEW — gate admin-only views
├── EmailVerificationBanner.tsx       # NEW
├── LoginForm.tsx / RegisterForm.tsx  # NEW
app/
├── login/page.tsx                    # NEW
├── register/page.tsx                 # NEW
├── verify-email/page.tsx             # NEW   (reads ?token=)
├── account/profile/page.tsx          # NEW
├── account/change-password/page.tsx  # NEW
├── account/users/page.tsx            # NEW   (admin-only)
└── layout.tsx                        # CHANGE — wrap in AuthProvider + banner
```

---

## API changes (this task owns)

### User model additions

> **Backward-compatibility:** both fields must have **defaults** so existing user records
> (created without them) still validate on read.

| Field         | Type          | Default | Notes                                  |
| ------------- | ------------- | ------- | -------------------------------------- |
| `name`        | `str \| None` | `None`  | Optional; editable on profile          |
| `is_verified` | `bool`        | `False` | Set true after email verification      |

### New TinyDB tables

- `refresh_tokens` — `{ id, user_id, token_hash, expires_at, revoked }` (revocable/rotating).
- `email_verifications` — `{ user_id, token_hash, expires_at, used }`.

### New endpoints

| Method | Path                         | Auth   | Purpose                                             |
| ------ | ---------------------------- | ------ | -------------------------------------------------- |
| POST   | `/auth/refresh`              | cookie | Rotate refresh cookie, return new access token      |
| POST   | `/auth/logout`               | cookie | Revoke this refresh token, clear cookie             |
| POST   | `/auth/logout-all`           | Bearer | Revoke all of the user's refresh tokens             |
| POST   | `/auth/verify-email`         | public | Consume verification token, set `is_verified`       |
| POST   | `/auth/resend-verification`  | Bearer | Re-issue verification email (stub)                  |
| GET    | `/users`                     | admin  | Restricted from "any authenticated" to admin-only   |

Login/register also create a refresh-token record and set the HttpOnly cookie.

### New environment variables (`services/api/.env.example`)

| Variable                     | Example                   | Purpose                                  |
| ---------------------------- | ------------------------- | ---------------------------------------- |
| `REFRESH_TOKEN_EXPIRES_DAYS` | `7`                       | Refresh-token lifetime                   |
| `REFRESH_COOKIE_NAME`        | `brasaland_refresh`       | Cookie name middleware checks            |
| `COOKIE_SECURE`              | `false` (dev)/`true`(prod)| `Secure` flag on the refresh cookie      |
| `FRONTEND_BASE_URL`          | `http://localhost:3000`   | Base for verification email links        |

---

## Authentication & account views

- **`/login`** — form-encoded `POST /auth/login`; success stores the access token + receives
  the refresh cookie, redirects to `/`; failure shows an inline error.
- **`/register`** — JSON `POST /auth/register` (`email, password, name`); maps `422 detail[]`
  to field errors and `400` duplicate-email to the email field; then triggers a verification email.
- **`/verify-email?token=`** — calls `POST /auth/verify-email`; shows success/expired states.
- **`/account/profile`** — shows `name`/`email` from `GET /auth/me`; edits `name` via `PUT /users/{id}`.
- **`/account/change-password`** — current/new/confirm; validates match + policy, then `PUT /users/{id}`.
- **`/account/users`** (admin-only) — lists users; toggles `is_admin`/`is_active`; delete.

---

## Token lifecycle

| Event                      | Action                                                                 |
| -------------------------- | --------------------------------------------------------------------- |
| Login / Register           | Store access token (localStorage); server sets HttpOnly refresh cookie |
| Every protected API call   | Attach `Authorization: Bearer <access>`                               |
| Access call returns `401`  | Single-flight `/auth/refresh` (cookie) → new access token → retry      |
| Refresh fails              | Clear access token + cookie, redirect `/login`                         |
| Logout                     | `POST /auth/logout` (revoke + clear cookie), clear localStorage, redirect |

---

## Route protection

- **Middleware (`middleware.ts`):** if the refresh cookie is absent on a protected path,
  redirect to `/login`. `matcher` excludes `/login`, `/register`, `/verify-email`,
  `/_next`, and static assets — and never the website.
- **`AuthGuard`:** client-side; ensures a valid access token (refreshing if needed) and
  reacts to `401`.
- **`AdminGuard`:** wraps `/account/users`; non-admins are redirected/blocked (the API also enforces).
- **Public website:** no middleware, no guard.

---

## Email (dev stub)

`email/sender.py` exposes `send_email(to, subject, body)` that, in dev, **prints the link to
the console / writes to a log file**. Verification links point at the backoffice
`${FRONTEND_BASE_URL}/verify-email?token=…`. A single interface so a production
SMTP/provider can be dropped in without touching call sites.

---

## Risks, mitigations & implementation guidance

**Correctness-critical**

- **Same-origin cookies.** Auth/refresh/logout must go through the Next rewrite proxy with
  `credentials: "include"`; cookie `Path=/`, host-only (no Domain). Cross-origin would force
  `SameSite=None; Secure` + CORS `allow_credentials` — avoid.
- **Single-flight refresh.** Concurrent `401`s must share one in-flight refresh promise in
  `http.ts`; otherwise parallel refreshes invalidate each other under rotation.
- **No redirect loop.** On refresh failure, clear the **HttpOnly cookie server-side**
  (`/auth/logout` → `Set-Cookie … Max-Age=0`); otherwise middleware keeps seeing the cookie
  and bounces the user back. Access token + cookie are always set/cleared together.

**Security**

- **Refresh-token rotation + reuse detection:** issue a new refresh token each refresh and
  revoke the old; if a revoked token is replayed, revoke the whole family (theft signal).
- **localStorage XSS trade-off** is accepted per the ticket; keeping the refresh token
  HttpOnly limits a stolen access token to ~30 min.

**Backward-compatibility**

- `name`/`is_verified` ship with defaults (above) so pre-existing users validate on read.

**Testing impact**

- Restricting `GET /users` to admins **breaks** `test_update_other_user_forbidden` (it lists
  users as a non-admin). Update it to seed/use an admin.
- `conftest.py` must reset the new `refresh_tokens`/`email_verifications` tables; the
  auth-bypass `client` fixture must satisfy `require_admin` (its override user is `is_admin`).

**UX**

- `AuthProvider` reads localStorage in `useEffect` and renders a neutral loading state to
  avoid hydration mismatch.
- Reuse one error-mapping helper (the existing `formatApiError` pattern: `422 detail[]`,
  `400`, `401`, `403`) across all new clients.

---

## Execution order

1. API: add `name`/`is_verified` (with defaults); refresh-token table + `/auth/refresh` +
   `/auth/logout` + `/auth/logout-all`.
2. API: email verification endpoints + email stub.
3. API: restrict `GET /users` to admin; update the affected test; confirm `PUT` role toggles.
4. Backoffice: `next.config.mjs` rewrites; `auth-storage` + `http.ts` (single-flight refresh).
5. Retrofit suppliers/incidents clients; verify against a real protected route.
6. Views: login/register → middleware/guards → account (profile, change-password) →
   verify-email → admin users.
7. Tests.

---

## Testing

- **API (pytest):** refresh rotation + revocation + reuse detection; logout/logout-all
  invalidate refresh; verify-email single-use + expiry; admin-only `GET /users` (403 for
  non-admin); `name` round-trips; existing suite still green (update the ownership test).
- **Backoffice (vitest/RTL):** login/register success+error; single-flight `401 → refresh →
  retry`; refresh-failure → clear + redirect; protected route w/o cookie → redirect; admin
  guard; verify-email token screen.
- **Manual:** register → verify banner → verify link → use app → token expiry auto-refresh →
  logout blocks protected routes.

---

## Criteria traceability

| Requirement | Artifact |
| --- | --- |
| `/login`, store token, redirect, error | `app/login` + `LoginForm` + `auth-storage` |
| `/register`, field-level errors | `app/register` + `RegisterForm` |
| `/account/profile` edit name | `app/account/profile` (+ `name` field) |
| `/account/change-password` match check | `app/account/change-password` |
| Token in localStorage + Bearer everywhere | `auth-storage` + `http.ts` + retrofits |
| Middleware redirect | `middleware.ts` (refresh cookie) |
| Logout clears + redirects | `AuthProvider.logout` + `/auth/logout` |
| `401` → clear + redirect | `http.ts` (after refresh fails) |
| Public website unaffected | no `uis/website` changes |
| Refresh tokens | refresh table + `/auth/refresh` + retry |
| Email verification | `/verify-email` + banner + endpoints |
| Role admin | `/account/users` + admin restriction |

---

## Implementation notes / deviations

- **Email package named `mailer/`, not `email/`.** A top-level `email` package would
  shadow Python's stdlib `email` (imported by FastAPI/pandas) because the API runs with
  `pythonpath = ["."]`. The module is otherwise as described.
- **Next.js 16 deprecation:** `middleware.ts` builds and runs (reported as "Proxy
  (Middleware)") but Next 16 prefers the new `proxy.ts` convention. Kept as `middleware.ts`
  to match the ticket's terminology; can be migrated to `proxy.ts` later with no behavior change.
- **Change-password** verifies the current password by calling `/auth/login` before issuing
  the `PUT /users/{id}` update (the AUTH-01 `PUT` does not check the old password itself).
- **`/` and `/candidates/[id]`** call the external 4Geeks tracker API (not the Brasaland API),
  so they are session-gated by middleware but do not attach our Bearer token.

## Deferred (later updates)

- **Password reset** (`/auth/forgot-password`, `/auth/reset-password`) — planned for a
  later update.
- Real SMTP / email provider (stubbed for now).
- Social / OAuth login, MFA.
- Audit logging of auth events.

---

_Internal document — 4Geeks Academy · AI Engineering Track_
