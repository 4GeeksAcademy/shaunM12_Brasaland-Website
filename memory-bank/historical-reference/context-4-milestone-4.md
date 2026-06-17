# CONTEXT - Brasaland

## AI Engineering - 4Geeks Academy

> Source: milestone 4 implementation summary (current repository state)

### Milestone Focus

Milestone 4: integrated delivery hardening (public website + tracker backoffice + API flows + integration tests).

---

## Milestone 4 Requirement Baseline

This section captures the required milestone baseline in a normalized, auditable format.

### Agent infrastructure

1. Create the `memory-bank/` folder at the root of the monorepo with at least the following files:
	- `projectbrief.md`: business description, project objectives, and the problems it solves.
	- `techContext.md`: tech stack, architectural decisions made, and technical constraints.
	- `progress.md`: current state of development and planned next steps.
2. Create the `agents.md` file at the root of the monorepo defining:
	- Which memory bank files the agent must read at the start of each session.
	- The mandatory workflow before each commit (minimum 4 ordered, explicit steps).
	- The folders and files the agent must not modify without explicit developer confirmation.
3. Create the `.agents/` folder with at least one development rule documented with its scope (always active, file-pattern based, or agent-requested), including:
	- A single, clearly defined objective.
	- Documented inputs.
	- Explicit and verifiable acceptance criteria.

Important alignment rule:

- The memory bank, rules, and skill must be aligned with the data, processes, and constraints defined in `context-4-milestone-4.md`.
- A generic infrastructure that ignores the company context is not acceptable.

### Next.js + TypeScript application

1. Initialize the frontend structure under `/uis` inside the monorepo following the template repository structure.
2. Create the public web project in `./uis/website` (Next.js + TypeScript).
3. Migrate and improve the corporate website from milestone 1 in `./uis/website` as the home route (`/`), ensuring:
	- All sections from milestone 1 are present and complete.
	- Implementation uses reusable React components and correct TypeScript typing.
	- Styles are consistent with the visual identity established in milestone 1.
4. Create the internal app in `./uis/backoffice`, ensuring:
	- Route `/` in `./uis/backoffice` is accessible with a basic entry view (welcome screen or empty dashboard structure).
	- It has its own layout separate from the public corporate website layout in `./uis/website`.
5. Integrate the TypeScript script from the business logic module (milestone 2) inside `./uis/backoffice`, ensuring:
	- Code is imported from its original location in the monorepo, not copied.
	- The output of the business logic is visible in the interface (not only in the console).

---

## Scope Delivered

This milestone consolidates the previous increments into a production-ready baseline:

- Public website preserved and connected to Brasa Points registration.
- Backoffice tracker aligned with API standards and async UX states.
- Candidate detail lifecycle completed (read, update, notes, delete).
- Integration tests added for key user workflows.

---

## Public Website (Milestone 1 Continuity)

### Registration Access Restored

Brasa Points registration is accessible from both CTAs in the website UI and routes to:

- /application.html

Static assets are served from:

- uis/website/public/application.html
- uis/website/public/validation.js
- uis/website/public/validation-shared.js

### CTA Wiring

- Hero CTA links to /application.html.
- Brasa Points section CTA links to /application.html.
- Registration page "Back to home" links to /.

---

## Backoffice Tracker (Milestone 3 + Milestone 4 Hardening)

### API Standardization

Backoffice uses API base URL standard:

- NEXT_PUBLIC_TRACKER_API_BASE_URL
- no fallback in code; runtime requires NEXT_PUBLIC_TRACKER_API_BASE_URL to be set.

Implemented API operations include:

- GET /records
- GET /records/{id}
- POST /records
- PUT /records/{id}
- PATCH /records/{id}
- DELETE /records/{id}
- GET /records/{id}/notes
- POST /records/{id}/notes
- DELETE /records/{id}/notes/{note_id}

### Routing and Views

- Candidate list view at /
- Candidate detail view at /candidates/[id]
- Query-parameter filters for status, stage, and search on list view.

### Async UX States

Request lifecycle is normalized via a shared hook with explicit states:

- idle
- loading
- success
- error

### Candidate Detail Capabilities

- Full candidate profile display.
- Status and stage updates via PATCH.
- Full candidate edit via PUT.
- Notes add/delete in detail view.
- Candidate delete with confirmation.

---

## Type and Structure Requirements

### Types

Tracker API-facing types include:

- Candidate
- CandidateInput
- CandidatePatchInput
- CandidateNote
- AsyncState

### Organization

Backoffice structure follows required separation:

- app
- components
- hooks
- lib
- types

---

## Integration Test Coverage

Integration tests were introduced for the backoffice app using Vitest + Testing Library.

### Covered Flows

- List page initial fetch and filter/search query-param behavior.
- Candidate create flow and subsequent list refresh.
- Candidate detail load (record + notes).
- Status update flow.
- Full candidate replace flow.
- Add note and delete note flows.
- Candidate delete and redirect flow.

### Test Tooling

- vitest
- jsdom
- @testing-library/react
- @testing-library/jest-dom
- @testing-library/user-event

---

## Verification Audit (Current Repo)

Status legend:

- COMPLETE: criterion is currently implemented in active runtime paths.
- PARTIAL: criterion is implemented in part, or drifted after refactors.

### Milestone 1 Criteria

- COMPLETE: public website exists in `uis/website` with all required sections and typed reusable components.
- COMPLETE: Brasa Points registration route is reachable at `/application.html` via website CTAs.

### Milestone 2 Criteria

- COMPLETE: business logic utilities are implemented in `src/utils` and covered by tests under `tests/`.
- COMPLETE: root TypeScript utility module remains importable from monorepo apps.

### Milestone 3 Criteria

- COMPLETE: backoffice list/detail routes are implemented with API-backed CRUD and notes flows.
- COMPLETE: async loading/success/error states are present for major API interactions.

### Milestone 4 Baseline Criteria

- COMPLETE: `.agents/` exists with rules and skill files.
- COMPLETE: `memory-bank/projectbrief.md`, `memory-bank/techContext.md`, and `memory-bank/progress.md` exist.
- COMPLETE: required root `agents.md` exists and defines startup reads, mandatory commit workflow, and protected paths.
- COMPLETE: `uis/website` and `uis/backoffice` are active and wired.
- PARTIAL: backoffice currently renders live KPI cards and list analytics; milestone-2 shared-module snapshot cards are not currently visible in runtime UI.

### Duplication and Legacy Cleanup Accuracy

- COMPLETE: legacy `uis/brasaland-webpage` runtime content has been retired.
- PARTIAL: a non-runtime leftover artifact remains at `uis/talent-pipeline-tracker/app/favicon.ico` due environment-level deletion constraints.

---

## Acceptance Snapshot

Current repository status for milestone 4 baseline:

- Website build passes.
- Backoffice build passes.
- Backoffice integration tests pass.
- Registration access is restored from the public site.
- Root `agents.md` is implemented.
- Milestone-2 business-logic utility modules are implemented and tested, but dedicated snapshot-card visibility in backoffice UI is not currently present.

---

## Notes for Next Milestone

Recommended next objectives:

- Add end-to-end browser tests for website registration route and backoffice critical journeys.
- Add CI workflow to run build + tests for both uis/website and uis/backoffice on each PR.
- Add API contract guards for response-shape drift (runtime parsing or schema validation).

---

_Internal document - 4Geeks Academy · AI Engineering Track_
_Repository historical reference for milestone continuity_
