# CONTEXT — Error-Handling Audit (Analysis) · Brasaland

## AI Engineering - 4Geeks Academy

> **Task:** ERR-01 — Error-handling audit (analysis artifact)
> **Repository index:** `context-9-error-handling-audit.md`
> **Companion plan:** `context-9-error-handling.md` (the execution plan derived from this audit)
> **Type:** Point-in-time assessment (read-only audit; no changes)

## Scope reviewed

- **Frontend:** `uis/backoffice` (all real `fetch`/async UI) and `uis/website` (public registration form).
- **Backend:** `services/api`.
- **Scripts:** `scripts/` (`analyze.py`, `build_incidents_csv.py`).

## Categories used

1. Missing try/catch — async ops (fetch, await, file I/O, JSON parsing) with no error handling.
2. Overly broad catch — try/except wrapping whole functions instead of the dangerous op.
3. Silent failures — swallowed errors (empty catch, bare `except: pass`).
4. Raw error exposure — raw exception/stack/status reaching the UI or API response.
5. Sensitive data leaks — secrets, connection strings, internal paths, or PII in error output/logs.
6. Missing loading/error UI states — components that fetch but render nothing / crash on loading or failure.
7. No user call to action — error states with no retry / navigation / support path.
8. Missing `sys.exit` on script failure — scripts that hit a critical error but don't exit non-zero.

---

## CRITICAL

### 1. Auth tokens written to logs via the default email provider
- **Location:** `services/api/mailer/providers.py:29-38` (`_send_console`); default provider (`config.EMAIL_PROVIDER` defaults to `"console"`).
- **Category:** 5 — Sensitive data leak
- **Problem:** `_send_console` `print()`s the full email body, which includes the password-reset / verification **link with its token**, to stdout/logs. Because `console` is the default, any environment that doesn't explicitly set `EMAIL_PROVIDER` leaks reset tokens (account-takeover risk) into logs.
- **Suggested fix:** Gate console output behind an explicit `APP_ENV=dev` check; never print token/links otherwise; make the default fail-closed (raise/no-op) in non-dev.

---

## HIGH

### 2. Unguarded email send can 500 and leak provider errors
- **Location:** `services/api/auth/routes.py:185-186` (`resend_verification`)
- **Category:** 1 — Missing try/catch (and 4 — raw error exposure)
- **Problem:** `send_verification_email(...)` has no error handling here (unlike the `register`/`forgot_password` sites). A provider/network failure (`httpx` error or `raise_for_status`) propagates → HTTP 500 with a raw exception that may contain the provider's response.
- **Suggested fix:** Wrap in `try/except`, log server-side, return a generic "verification email queued" message.

### 3. Raw pandas parser error forwarded to the API response
- **Location:** `services/api/incident_analyzer/analyzer.py:21-22` → surfaced at `services/api/main.py:70-74`
- **Category:** 4 — Raw error exposure
- **Problem:** The raw pandas exception text is wrapped into `ValueError(f"Incorrect CSV format: {exc}")` and returned verbatim in the `HTTPException` `detail`, which the frontend renders to the user.
- **Suggested fix:** Log the full parser error server-side; return a generic, user-safe message (e.g., "The CSV could not be parsed").

---

## MEDIUM

### 4. Silent + overly broad catch around password-reset email
- **Location:** `services/api/auth/routes.py:225-230`
- **Category:** 2 & 3 — Overly broad catch / silent failure
- **Problem:** `except Exception: pass` (no logging). Anti-enumeration justifies a constant *response*, but swallowing all errors silently means real delivery failures are invisible to ops and users never get the reset link.
- **Suggested fix:** Keep the generic response, but `logger.exception(...)` the failure and narrow the caught types.

### 5. Silent + broad catch around verification email on register
- **Location:** `services/api/auth/routes.py:99-103`
- **Category:** 3 — Silent failure
- **Problem:** `except Exception: pass` with no logging; hides misconfiguration/provider errors.
- **Suggested fix:** Log at warning/error; narrow to expected exceptions.

### 6. CSV build script has no IO error handling or explicit failure exit
- **Location:** `scripts/build_incidents_csv.py:62` (`pd.read_csv(SOURCE)`), `:93` (`to_csv`), `:97-98` (`if __name__ == "__main__": build()`)
- **Category:** 1 & 8 — Missing try/catch (file I/O) / missing `sys.exit` on failure
- **Problem:** A missing/locked source file or write failure dumps a raw traceback; `build()` has no `try/except` and no explicit `sys.exit(1)` path (unlike the well-structured `analyze.py`).
- **Suggested fix:** Wrap read/write in `try/except`, print a friendly message to `stderr`, and `raise SystemExit(1)` on failure.

### 7. PII (recipient email) logged on every send
- **Location:** `services/api/mailer/providers.py:37, 57, 81`
- **Category:** 5 — Sensitive data leak (minor)
- **Problem:** `logger.info("...to %s...", to, subject)` records customer/user email addresses in logs.
- **Suggested fix:** Drop or redact the address, or move to debug-level.

### 8. Frontend error states with no call to action
- **Location:** `uis/backoffice/app/incidents/page.tsx:67-71`, `uis/backoffice/app/suppliers/page.tsx:78` (error passed to `SupplierDirectory`), `uis/backoffice/app/candidates/[id]/page.tsx:190-192`
- **Category:** 7 — No user call to action
- **Problem:** These correctly show an error message but offer no **retry**, navigation, or support path.
- **Suggested fix:** Add a "Retry" action that re-invokes the loader (`loadSuppliers` / `handleAnalyze` / `fetchCandidate`) and/or a support link.

---

## LOW

### 9. Server-component pages have no error/loading boundary
- **Location:** `uis/backoffice/app/data-processing/page.tsx:18-21`, `uis/backoffice/app/registration-analytics/page.tsx` (async `getRegistrations`)
- **Category:** 6 — Missing loading/error UI state
- **Problem:** No `try/catch` and no route-level `error.tsx`/`loading.tsx`. Safe today (in-memory sample data), but `registration-analytics` is already `async` and will 500 with no friendly UI once wired to a real API.
- **Suggested fix:** Add `app/.../error.tsx` (and `loading.tsx`) boundaries; wrap the async data call.

### 10. Unwrapped mutations in candidate detail
- **Location:** `uis/backoffice/app/candidates/[id]/page.tsx:128-153` (`handleReplace`, `handleAddNote`, `handleDeleteNote`)
- **Category:** 1 — Missing try/catch
- **Problem:** These API calls aren't guarded here (they rely on child components), and `handleDeleteNote` optimistically updates local state before the server confirms.
- **Suggested fix:** Wrap and surface errors; only mutate local state after the call resolves.

### 11. Unhandled results export write
- **Location:** `scripts/analyze.py:37-40` (`export_results`)
- **Category:** 1 — Missing try/catch (file I/O)
- **Problem:** `to_csv("results.csv")` isn't guarded; a permission/disk error tracebacks *after* a successful analysis.
- **Suggested fix:** Wrap the write, report a friendly error, exit non-zero if it matters.

### 12. Public application form reports success without submitting
- **Location:** `uis/website/public/validation.js:420-431`
- **Category:** 6/7 — (observation)
- **Problem:** On valid input it shows "you'll receive a confirmation email" but performs **no** network submission, so there's no real error path. If a real POST is added later, it currently has zero submit-error handling.
- **Suggested fix:** When wiring a real submit, add `try/catch` around the request with a failure message + retry.

---

## Already solid (reviewed, not flagged)

- `scripts/analyze.py:54-75` — proper `try/except`, `stderr` reporting, `return 1`, and `raise SystemExit(main())`. Good model for the other script.
- `uis/backoffice/lib/http.ts` — single-flight refresh; the `catch {}` at `:39` and the 401 paths are intentional/handled (redirect + thrown user-facing message), not silent.
- `uis/backoffice/app/suppliers/page.tsx` / `incidents/page.tsx` / `candidates/[id]/page.tsx` — real `loading`/`error` states (just missing the retry CTA in finding #8).
- `uis/backoffice/lib/api-error.ts`, `suppliers-api.ts`, `incidents-api.ts` — network failures distinguished from HTTP errors and mapped to friendly messages.

---

## Severity index

| Severity | Finding | Location |
| --- | --- | --- |
| CRITICAL | Reset/verification tokens printed to logs via default provider | `mailer/providers.py:29-38` |
| HIGH | Unguarded email send → 500 / raw provider error | `auth/routes.py:185-186` |
| HIGH | Raw pandas parse error returned to client | `analyzer.py:21-22` → `main.py:70-74` |
| MEDIUM | Silent broad catch on forgot-password email | `auth/routes.py:225-230` |
| MEDIUM | Silent broad catch on register email | `auth/routes.py:99-103` |
| MEDIUM | Script IO/CSV unguarded + exit code | `build_incidents_csv.py:62,93,97-98` |
| MEDIUM | PII (recipient email) logged at info | `mailer/providers.py:37,57,81` |
| MEDIUM | Frontend error states with no call to action | suppliers / incidents / candidates pages |
| LOW | Server components without error/loading boundary | `data-processing/`, `registration-analytics/` |
| LOW | Unwrapped candidate mutations | `candidates/[id]/page.tsx:128-153` |
| LOW | Unguarded results export write | `analyze.py:37-40` |
| LOW | Public form reports success without submitting | `website/public/validation.js:420-431` |

---

## Suggested fix order

1. #1 (token-in-logs default) and #3 (raw parser error) — security/exposure.
2. #2 (unguarded send) and #4/#5 (silent email failures + logging).
3. #6 (script robustness), #8 (retry CTAs).
4. Remaining LOW items.

See `context-9-error-handling.md` for the full execution plan, conventions, and verification steps derived from this audit.
