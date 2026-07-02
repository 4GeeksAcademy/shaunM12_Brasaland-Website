# CONTEXT — Centralized Incident Manager · Brasaland

## AI Engineering - 4Geeks Academy

> **Repository index:** `context-13-centralized-incident-manager.md`  
> **Companion docs:** `context-5-incident-file-analyzer.md`, `context-9-error-handling.md`  
> **Type:** Full-stack feature (incidents domain)  
> **Status:** Implemented baseline (backend + frontend + seed)

---

## Business Objective

Brasaland needs one centralized operational workflow to register, track, and report incidents across all branches.  
This context defines the canonical incident model and the required backend/frontend behavior so branch operations and leadership can work from one source of truth.

---

## Canonical Domain Values

### Branches

- `central`
- `medellin_centro`
- `medellin_laureles`
- `medellin_envigado`
- `medellin_bello`
- `medellin_itagui`
- `bogota_chapinero`
- `bogota_usaquen`
- `cali_granada`
- `barranquilla_norte`
- `miami_doral`
- `miami_hialeah`
- `miami_kendall`
- `orlando_international`
- `fort_lauderdale`

### Categories

- `equipment_failure`
- `supply_issue`
- `customer_complaint`
- `staff_issue`
- `facility_issue`
- `pos_system`
- `delivery_issue`
- `other`

### Origins

- `customer`
- `branch`
- `internal`

### Statuses

- `open`
- `in_progress`
- `resolved`
- `discarded`

### Allowed lifecycle transitions

- `open -> in_progress | discarded`
- `in_progress -> resolved | discarded`
- terminal: `resolved`, `discarded`

---

## Data Model

### `incident`

- `id` (int, PK)
- `title` (string, required)
- `description` (string, required)
- `category` (enum-like string, required)
- `status` (enum-like string, default `open`)
- `origin` (enum-like string, required)
- `branch` (enum-like string, required)
- `created_at` (datetime, UTC)
- `updated_at` (datetime, UTC)

### `incident_seed_key`

Idempotency mapping for historical import without storing legacy IDs on `incident`.

- `id` (int, PK)
- `source_key` (string, unique)
- `incident_id` (FK -> `incident.id`)
- `created_at` (datetime, UTC)

---

## API Scope

### Required endpoints

- `POST /api/incidents`  
  Create incident with canonical validation and normalized payload.

- `GET /api/incidents`  
  List incidents with optional filters: `status`, `origin`, `branch`, `category`.

- `GET /api/incidents/{id}`  
  Fetch one incident or return `404`.

- `PATCH /api/incidents/{id}/status`  
  Enforce lifecycle transitions; reject invalid transitions with `400`.

- `GET /api/incidents/summary`  
  Aggregated totals grouped by status/category/origin/branch.

### Error handling requirements

- Canonical validation errors return user-safe `400`.
- Missing records return `404`.
- Unexpected failures return structured `500` without leaking internals.

---

## Seed / Historical Import Rules

- Source file: `data/incidents-brasaland.csv`.
- Normalize legacy values (category, status, date).
- Map legacy location IDs into canonical `branch` values.
- Import must be idempotent via `incident_seed_key.source_key`.
- Invalid records must be reported and skipped safely.

---

## Frontend Scope (Backoffice)

### Core pages

- Incident list page with filters + status updates.
- New incident registration page.
- Incident summary/metrics page.

### UX requirements

- Loading, empty, and error states.
- Friendly API validation messages.
- Canonical enum options in forms.
- Safe status-transition UX (no invalid transition actions).

---

## Implementation Reference (Repository)

- Backend domain:
  - `services/api/incidents/models.py`
  - `services/api/incidents/schemas.py`
  - `services/api/incidents/constants.py`
  - `services/api/incidents/repository.py`
  - `services/api/incidents/routes.py`
- API integration:
  - `services/api/main.py`
- Frontend:
  - `uis/backoffice/lib/incidents-api.ts`
  - `uis/backoffice/components/incidents/*`
  - `uis/backoffice/app/incidents/*`
- Seed data:
  - `data/incidents-brasaland.csv`

---

## Acceptance Criteria

- Incidents can be created, listed, filtered, updated, and summarized.
- Status transitions are enforced per lifecycle policy.
- Historical incident import is idempotent and reproducible.
- Frontend pages expose the centralized incident workflow end-to-end.
- Error behavior is aligned with context-9 error-handling conventions.

---

_Internal document — 4Geeks Academy · AI Engineering Track · Brasaland_
