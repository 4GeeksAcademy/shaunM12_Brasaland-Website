# CONTEXT — Error-Handling Execution Roadmap · Brasaland

## AI Engineering - 4Geeks Academy

> **Task:** ERR-01 — Execution roadmap for the error-handling hardening
> **Repository index:** `context-9-error-handling-execution-roadmap.md`
> **Companion plan:** `context-9-error-handling.md` (strategy, principles, conventions)
> **Companion audit:** `context-9-error-handling-audit.md` (the analysis / findings)
> **Type:** Hardening / engineering (no new features)
> **Status:** 🟡 Planned (not yet implemented)

### Locked execution decision (recommendation A)

- **Standardize all async views on the existing `useApiState` hook**
  (`uis/backoffice/hooks/useApiState.ts`), which already provides `state` /
  `data` / `error` / `execute` with a built-in scoped try/catch.
- Refactor `app/suppliers/page.tsx` and `app/incidents/page.tsx` off their local
  `useState` bookkeeping onto `useApiState`; `app/candidates/[id]/page.tsx` already uses it.
- This trades a slightly larger diff for one consistent loading/error/success contract
  across the backoffice. It is wiring/consolidation only — **not a feature**.

### Grounding facts (verified in repo)

- `services/api/config.py` has **no `APP_ENV` / console-echo flag yet** (it has
  `EMAIL_PROVIDER`, `_as_bool`, `FRONTEND_BASE_URL`). WP1 adds an explicit flag.
- There are **no shared `components/ui/ErrorState` / `LoadingState`** components yet —
  WP0 creates them.
- `uis/backoffice/hooks/useApiState.ts` exists and is the foundation for the three-state UI.

---

## Work packages

### WP0 — Conventions (do first)

- **Goal:** build the primitives every later package reuses.
- **Files:**
  - Backend: `services/api/` — add a per-package module logger convention + a single
    helper that maps caught exceptions to a safe `{"detail": "<human message>"}` (e.g.
    `logger.exception(...)` at the catch site, generic `HTTPException` to the client).
  - Frontend (new): `uis/backoffice/components/ui/ErrorState.tsx`
    (message + **Retry** button + **Back to home** link + support hint) and
    `uis/backoffice/components/ui/LoadingState.tsx` (spinner/skeleton).
- **Criteria covered:** human-readable messages, clear exit, structured backend errors.
- **Gate:** `tsc --noEmit` clean; `pytest` green.

### WP1 — CRITICAL / HIGH backend + secrets

- **Goal:** close the security/exposure findings first.
- **Steps:**
  - **#1** `services/api/mailer/providers.py:29-38` (`_send_console`) — gate the `print()`
    behind a new explicit dev flag in `config.py`; never echo token/links otherwise;
    fail-closed default.
  - **#3** `services/api/incident_analyzer/analyzer.py:21-22` + `services/api/main.py:70-74`
    — stop forwarding the raw pandas message; log it server-side; return a generic
    "CSV could not be parsed".
  - **#2** `services/api/auth/routes.py:185-186` (`resend_verification`) — wrap
    `send_verification_email` in try/except, log, return a generic message.
- **Criteria covered:** no sensitive data to client, no raw messages, external-call handling.
- **Gate:** new pytest cases (parse failure → generic; provider failure → no 500/leak).

### WP2 — Backend MEDIUM

- **Goal:** right-scope catches + remove PII from logs.
- **Steps:**
  - **#4/#5** `services/api/auth/routes.py:225-230` and `:99-103` — keep the constant
    anti-enumeration response, add `logger.exception`, narrow `except Exception` to
    expected types.
  - **Mailer HTTP** `services/api/mailer/providers.py` — guard `httpx.post` /
    `raise_for_status`; log provider/network errors; never raw to client.
  - **#7** `services/api/mailer/providers.py:37,57,81` — redact / lower recipient-email logs.
- **Criteria covered:** right-scope catches, no sensitive data, external-call handling.
- **Gate:** `pytest`; forgot-password still returns the constant message.

### WP3 — Frontend states & CTAs (recommendation A)

- **Goal:** uniform three-state UI on `useApiState`, with real CTAs.
- **Steps:**
  - Refactor `app/suppliers/page.tsx` and `app/incidents/page.tsx` to `useApiState`;
    render `LoadingState` / `ErrorState`.
  - **#8** wire `ErrorState` (with retry) into suppliers, incidents, and
    `app/candidates/[id]/page.tsx`; retry re-invokes `loadSuppliers` / `handleAnalyze` /
    `fetchCandidate`.
  - **#9** add `app/error.tsx` + `app/loading.tsx` (plus route-level boundaries for
    `app/data-processing/` and `app/registration-analytics/`).
  - **#10** `app/candidates/[id]/page.tsx:128-153` — wrap `handleReplace` /
    `handleAddNote` / `handleDeleteNote`; confirm server success before optimistic updates.
  - Sweep for optional chaining `?.`, safe defaults, and `finally { setLoading(false) }`
    across API libs and pages.
- **Criteria covered:** three visible states, human-readable messages, clear exit,
  optional chaining, safe defaults, finally blocks.
- **Gate:** `tsc --noEmit`; force a failing fetch per view.

### WP4 — Scripts

- **Goal:** robust file/CSV handling + correct exit codes.
- **Steps:**
  - **#6** `scripts/build_incidents_csv.py:62,93,97-98` — try/except around `read_csv` /
    `to_csv`, friendly `stderr` message, `raise SystemExit(1)`; mirror `analyze.py`.
  - **#11** `scripts/analyze.py:37-40` — guard the `to_csv` write.
  - Add defensive pre-checks (file exists, non-empty, required columns) before processing
    in both scripts.
- **Criteria covered:** try/except on file I/O + CSV, stderr messages, non-zero exit,
  defensive checks.
- **Gate:** run against missing + malformed CSV → friendly stderr + non-zero exit, no traceback.

### WP5 — General sweep

- **Goal:** remove sensitive output; close the website observation.
- **Steps:**
  - **#12** `uis/website/public/validation.js:420-431` — document the no-network path
    (no false "email sent"); add error handling only if a real POST is wired.
  - Grep all `print()` / `console.error|log|warn` for sensitive internal info; remove/replace.
- **Criteria covered:** remove sensitive print/console output.
- **Gate:** secret/PII grep of logs/output after exercising each flow.

---

## Final verification

- **Backend:** `pytest` (parse failure → generic message; provider failure → no 500/leak;
  forgot-password still constant while logging).
- **Frontend:** `tsc --noEmit`; each async view renders loading → error (with retry) →
  success; forced failing fetch shows no raw message and no crash.
- **Scripts:** run against missing + malformed CSV → `stderr` message + non-zero exit,
  no raw traceback.
- **Secrets:** grep logs/output for tokens, emails, and internal paths after each flow.

---

## Criteria coverage matrix

| Original criterion | Covered by |
| --- | --- |
| No error crashes / undefined state | WP3 (boundaries, finally), WP1–2 (no 500s) |
| 3 states per async op | WP0 + WP3 |
| Human-readable messages | WP0, WP1 (#3), WP3 |
| Clear exit (retry/home/support) | WP0 `ErrorState` + WP3 |
| Right-scope backend catches | WP1–2 |
| Clean structured JSON, no tracebacks | WP0, WP1 (#3), WP2 |
| No sensitive data to client | WP1 (#1), WP2 (#7) |
| External-call handling | WP1 (#2), WP2 (mailer) |
| Script I/O + CSV try/except → stderr | WP4 |
| Scripts exit non-zero on critical error | WP4 |
| Defensive input checks | WP4 |
| Remove sensitive print/console | WP5 |

---

## Commit / PR grouping

1. **WP0 + WP1** — conventions + critical/high backend & secrets (isolated, security-sensitive).
2. **WP2** — backend medium (catch scope, mailer HTTP, PII logs).
3. **WP3** — frontend three-state standardization + CTAs + boundaries.
4. **WP4 + WP5** — scripts hardening + general sensitive-output sweep.

---

## Out of scope (explicit)

No new endpoints/pages/features, no styling redesign, no data-model changes, no dependency
bumps, and no refactors unrelated to error handling.
