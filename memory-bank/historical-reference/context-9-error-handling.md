# CONTEXT — Coherent Error-Handling Strategy · Brasaland

## AI Engineering - 4Geeks Academy

> **Task:** ERR-01 — Cross-cutting error handling across frontend, backend, and scripts
> **Repository index:** `context-9-error-handling.md`
> **Companion audit:** `context-9-error-handling-audit.md` (the analysis this plan is derived from)
> **Companion roadmap:** `context-9-error-handling-execution-roadmap.md` (sequenced work packages)
> **Type:** Hardening / engineering (no new features)
> **Status:** 🟡 Planned (not yet implemented)

### Locked decisions

- **Scope is hardening only.** No new endpoints, pages, or features; no styling redesign,
  data-model changes, dependency bumps, or refactors unrelated to error handling.
- **Both frontends are in scope:** `uis/backoffice` (all real `fetch`/async UI) and
  `uis/website` (public registration form).
- **Reusable UI primitives are allowed:** introduce a single `ErrorState` and `LoadingState`
  component pair in the backoffice and reuse them everywhere. This removes duplicated/missing
  handling and is treated as in-scope (not a feature).
- **Backend error contract:** every handled error returns a clean structured JSON body
  (`{"detail": "<human message>"}`), raw exceptions are logged server-side via `logging`, and
  no traceback / internal path / secret ever reaches the client.
- **Anti-enumeration responses stay constant** (forgot-password) — we add logging behind them,
  we do not change the response.
- **Console email provider is fail-closed by default** — it must never print tokens/links
  outside an explicit dev flag.

---

## Focus

The system currently has no coherent error-handling strategy: API calls can silently fail,
loading states are missing, users see raw technical messages (or nothing at all), and
background scripts crash without useful output. This task audits the existing codebase and
applies a consistent error-handling strategy across all three layers.

---

## Non-negotiable principles

1. No error may crash the app or leave the user in an undefined state.
2. Every frontend async operation has three visible states: **loading, success, error**.
3. User-facing messages are human-readable — never a stack trace, status code, or JSON parse error.
4. Every error state offers a clear exit: **retry**, **link home**, or **contact-support** instructions.
5. Backend/scripts catch exceptions at the **right scope** — not one try/except around a whole function.
6. Sensitive data never appears in any error output sent to the client.

---

## Shared conventions (build these first, reuse everywhere)

- **Backend error helper + logging:** one module logger per package; `logger.exception(...)`
  at the catch site; scrub PII/secrets from log lines; clients only ever see a curated `detail`.
- **Frontend `ErrorState` component:** message + retry button + "Back to home" link + support
  hint. Reused by every async view.
- **Frontend `LoadingState` component:** spinner/skeleton, reused by every async view.
- **Frontend fetch contract:** every API helper throws a typed, human-readable `Error`; every
  caller wraps the specific call in `try/catch` + `finally` and renders the three states.

---

## Task checklists

> Full finding descriptions, categories, and severities live in the companion analysis:
> **`context-9-error-handling-audit.md`**. The lists below are the actionable work items.

### Frontend — `uis/backoffice` & `uis/website`

- [ ] Inventory every `fetch`/async call and confirm a `try/catch` scoped to that call:
      `lib/http.ts`, `lib/auth-api.ts`, `lib/suppliers-api.ts`, `lib/incidents-api.ts`,
      `lib/users-api.ts`, `lib/api.ts`, plus page/component callers.
- [ ] Implement the **three-state UI** for each async view. Existing-but-incomplete views
      (`app/suppliers/page.tsx`, `app/incidents/page.tsx`, `app/candidates/[id]/page.tsx`)
      have loading + error but **no retry CTA** — add `ErrorState` with a retry that
      re-invokes the loader (`loadSuppliers` / `handleAnalyze` / `fetchCandidate`).
- [ ] Add **server-component boundaries**: `app/error.tsx` + `app/loading.tsx` (and/or
      route-level ones for `app/data-processing/` and `app/registration-analytics/`), which
      currently have no try/catch or error boundary.
- [ ] Guard **unwrapped mutations** in `app/candidates/[id]/page.tsx:128-153`
      (`handleReplace`, `handleAddNote`, `handleDeleteNote`); confirm server success before
      optimistic local state changes.
- [ ] Replace any **raw messages** surfaced to users with human-readable copy; keep raw text
      in logs only (audit the `caught.message` render paths).
- [ ] Use **optional chaining `?.`** and **safe defaults/fallbacks** when rendering nested or
      possibly-undefined data (e.g. `result?.sourcePath`, candidate fields, notes arrays).
- [ ] Ensure **`finally { setLoading(false) }`** on every loader (verify existing, add missing).
- [ ] `uis/website/public/validation.js:420-431`: the form reports success without submitting.
      Document that there is no network path today (no false "email sent" on failure); if a
      real POST is added, it must use `try/catch` + failure message + retry.

### Backend — `services/api`

- [ ] **Unguarded external call:** `auth/routes.py:185-186` (`resend_verification`) — wrap
      `send_verification_email` in `try/except`, log server-side, return a generic message.
      Make all three email-send sites consistent.
- [ ] **Raw library error exposure:** `incident_analyzer/analyzer.py:21-22` → `main.py:70-74`.
      Stop forwarding the raw pandas message into `detail`; log it and return a generic
      "CSV could not be parsed".
- [ ] **Silent/broad catches:** `auth/routes.py:99-103` (register) and `:225-230`
      (forgot-password) — keep the constant anti-enumeration response, but `logger.exception`
      and narrow the caught exception types instead of `except Exception: pass`.
- [ ] Add error handling around **all outbound HTTP** in `mailer/providers.py`
      (`httpx.post` + `raise_for_status`) so provider/network failures are logged and never
      bubble raw to the client.
- [ ] Verify every route returns a clean structured JSON error (no traceback) and that no
      `detail` contains internal paths, secrets, or connection info.

### Scripts — `scripts/`

- [ ] `build_incidents_csv.py:62,93,97-98` — wrap `read_csv`/`to_csv` in `try/except` with an
      informative `stderr` message; add `raise SystemExit(<non-zero>)` on failure. Mirror the
      good pattern already in `analyze.py`.
- [ ] `analyze.py:37-40` (`export_results`) — guard the `to_csv` write.
- [ ] Add **defensive pre-checks** for missing/malformed input before processing (file exists,
      required columns present, non-empty) in both scripts.
- [ ] Confirm both scripts **exit non-zero** on any critical failure.

### General — sensitive output

- [ ] **Token-in-logs (default provider):** `mailer/providers.py:29-38` (`_send_console`)
      prints the full email incl. the reset/verification token+link, and `console` is the
      DEFAULT provider. Gate console output behind an explicit dev flag; never print
      tokens/links in non-dev; fail-closed by default.
- [ ] **PII in logs:** `mailer/providers.py:37,57,81` log recipient email at info level —
      redact or lower to debug.
- [ ] Sweep all `print()` / `console.error` / `console.log` for sensitive internal info and
      remove or replace.

---

## Execution phases

- **Phase 0 — Conventions:** backend error/log helper; frontend `ErrorState` + `LoadingState`.
- **Phase 1 — CRITICAL/HIGH backend & secrets:** token-in-logs default, unguarded send,
  raw pandas error to client.
- **Phase 2 — Backend MEDIUM:** silent email catches, provider HTTP error handling, PII logs.
- **Phase 3 — Frontend states & CTAs:** retry CTAs, error/loading boundaries, unwrapped
  mutations, optional-chaining/defaults/`finally` sweep.
- **Phase 4 — Scripts:** IO/CSV guards, exit codes, defensive input checks.
- **Phase 5 — General sweep:** print/console sensitive-data audit.

---

## Verification

- **Backend:** `pytest` — add cases for parse-failure → generic message, provider failure →
  no 500 / no leak, forgot-password still returns the constant message while logging.
- **Frontend:** `tsc --noEmit`; verify each async view renders loading → error (with retry) →
  success; force a failing fetch to confirm no raw message and no crash.
- **Scripts:** run against a missing file and a malformed CSV; confirm `stderr` message +
  non-zero exit code; confirm no raw traceback dump.
- **Secrets:** grep logs/output for tokens, emails, and paths after exercising each flow.

> **Prioritization:** see the severity index in `context-9-error-handling-audit.md`.

---

## Out of scope (explicit)

No new endpoints/pages/features, no styling redesign, no data-model changes, no dependency
bumps, and no refactors unrelated to error handling.
