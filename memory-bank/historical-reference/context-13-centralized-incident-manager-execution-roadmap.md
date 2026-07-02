# EXECUTION ROADMAP — Context 13 Centralized Incident Manager

## Purpose

This roadmap translates `context-13-centralized-incident-manager.md` into concrete work packages and completion checks.

---

## Locked Decisions

- Keep incident domain canonical values centralized in backend constants.
- Validate canonical values at API schema layer and reject invalid inputs.
- Enforce lifecycle transition rules in repository/service logic.
- Keep historical import idempotent using seed keys.
- Surface friendly errors in backoffice UI.

---

## Work Packages

### WP1 — Backend domain foundation

- Add incidents package scaffold.
- Define incident and seed-key models.
- Define canonical constants and status transitions.

**Exit check**
- Models create and migrate cleanly via SQLModel metadata startup.

### WP2 — API contract and validation

- Implement create/list/detail/status update/summary endpoints.
- Add schema-level validation and structured error parsing.
- Wire incidents router into API app.

**Exit check**
- Endpoint contract matches context-13 and returns expected status codes.

### WP3 — Historical import and idempotency

- Build CSV seed/import flow.
- Normalize legacy category/status/date.
- Map location IDs to canonical branches.
- Prevent duplicate imports via seed keys.

**Exit check**
- Re-running seed does not duplicate incidents.

### WP4 — Backoffice UI

- Implement incident listing page with filters.
- Implement registration form.
- Implement summary dashboard.
- Implement status update UX with transition safety.

**Exit check**
- Core incident workflows complete end-to-end from backoffice.

### WP5 — Reliability and tests

- Add backend tests for CRUD, filters, transitions, and summary.
- Add frontend integration checks for API behaviors and error handling.
- Validate typecheck/test health.

**Exit check**
- Test suite passes for incident manager modules.

---

## Criteria Coverage Matrix

- **Canonical enums:** WP1 + WP2
- **Transition enforcement:** WP2 + WP5
- **Seed idempotency:** WP3 + WP5
- **Operational UX:** WP4
- **Error handling alignment:** WP2 + WP4 + WP5

---

## Final Verification Checklist

- [ ] API starts with incidents router mounted.
- [ ] All incident endpoints return expected results.
- [ ] Seed import loads historical incidents and is idempotent.
- [ ] Backoffice pages load without module/runtime errors.
- [ ] Status transitions follow policy exactly.
- [ ] Typecheck/tests pass for touched modules.

---

_Companion to context-13 centralized incident manager_
