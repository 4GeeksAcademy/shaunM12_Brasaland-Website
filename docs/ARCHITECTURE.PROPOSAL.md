# ARCHITECTURE PROPOSAL - Brasaland Backend

## 1. Context and Scope Boundaries

Brasaland operates 14 restaurants across Colombia and the United States and is modernizing manual, fragmented processes across operations, procurement, marketing, and internal tracking workflows.

This proposal defines the target backend architecture for the next stage of Brasaland Digital.

In scope:
- Architectural pattern recommendation and justification.
- Backend folder/module structure and separation criteria.
- FastAPI endpoint and router organization by domain.
- Risks and points of attention if the structure is not followed.

Out of scope:
- Immediate implementation of backend services.
- Database migration scripts.
- Frontend refactors.

## 2. Recommended Architectural Pattern and Rationale

### Recommended pattern
Domain-Oriented Layered Architecture implemented as a Modular Monolith with FastAPI.

### Why this is the best fit for Brasaland now
1. Multi-country operations need clear domain boundaries.
Brasaland runs in two countries with different operational realities. Domain boundaries reduce cross-team confusion and keep business rules explicit.

2. Current complexity does not justify microservices yet.
The company needs speed, consistency, and low operational overhead. A modular monolith gives strong internal separation without distributed-system complexity.

3. Existing pain points are cross-functional but connected.
Operations, procurement, loyalty, and talent tracking share data and decisions. A modular monolith allows phased domain rollout while preserving one source of truth.

4. Reliability of metrics is a business-critical requirement.
Leadership decisions depend on trusted data. Layered architecture makes validation, business rules, and persistence responsibilities explicit and auditable.

5. FastAPI aligns with current needs.
FastAPI supports typed contracts, validation, async I/O, and clear router composition, all needed for stable internal and public-facing integrations.

### Alternatives considered
1. MVC as primary pattern.
Rejected as the main pattern because it tends to mix transport and business concerns in growth stages and offers weaker domain boundary discipline.

2. Serverless-first architecture.
Deferred because it can increase operational fragmentation, local development complexity, and observability overhead at Brasaland's current stage.

3. Immediate microservices.
Rejected for now due to coordination and deployment overhead that is higher than current domain scale requires.

## 3. Proposed Backend Structure (Folders and Modules)

Proposed root structure:

- backend/
- backend/app/
- backend/app/main.py
- backend/app/api/
- backend/app/api/routers/
- backend/app/api/schemas/
- backend/app/application/
- backend/app/application/use_cases/
- backend/app/domain/
- backend/app/domain/candidates/
- backend/app/domain/operations/
- backend/app/domain/procurement/
- backend/app/domain/loyalty/
- backend/app/infrastructure/
- backend/app/infrastructure/persistence/
- backend/app/infrastructure/external/
- backend/app/shared/
- backend/app/shared/config/
- backend/app/shared/errors/
- backend/app/shared/logging/
- backend/tests/
- backend/tests/unit/
- backend/tests/integration/

## 4. Responsibility Separation Criteria

1. API layer.
Owns HTTP concerns only: request parsing, response formatting, auth boundaries, and status codes.

2. Application layer.
Owns use-case orchestration: transaction flow, policy sequencing, and coordination between domain and infrastructure.

3. Domain layer.
Owns business language and rules: entities, value objects, invariants, and domain services. Domain code must not depend on FastAPI, database clients, or framework utilities.

4. Infrastructure layer.
Owns technical adapters: repositories, external API clients, and persistence implementations. Infrastructure depends on domain contracts, never the opposite.

5. Shared layer.
Owns cross-cutting capabilities: configuration, structured logging, error mapping, and security primitives. Shared modules must not become a hidden business layer.

6. Testing separation.
Unit tests validate domain/application logic. Integration tests validate API contracts and adapter behavior.

## 5. FastAPI Endpoint and Router Organization by Domain

### Grouping criteria
1. Group routes by bounded context and aggregate ownership, not by HTTP verb.
2. Keep write and read flows near the same domain aggregate when they share lifecycle rules.
3. Place cross-domain endpoints in dedicated system routers only when they do not belong to one business context.

### Proposed API base prefix
- /api/v1

### Router groups and route inventory

1. System router: /api/v1/system
- GET /health
- GET /ready
- GET /version
Purpose: operational status, deployment checks, and runtime diagnostics.

2. Candidates router: /api/v1/candidates
- GET /
- POST /
- GET /{candidate_id}
- PUT /{candidate_id}
- PATCH /{candidate_id}
- DELETE /{candidate_id}
Purpose: core candidate lifecycle management for talent pipeline.

3. Candidate notes router: /api/v1/candidates/{candidate_id}/notes
- GET /
- POST /
- DELETE /{note_id}
Purpose: notes managed as a child resource under the candidate aggregate.

4. Operations router (phase-ready): /api/v1/operations
- GET /locations
- GET /locations/{location_id}/performance
- GET /waste
Purpose: location-level operational KPIs and waste tracking domain.

5. Procurement router (phase-ready): /api/v1/procurement
- GET /suppliers
- GET /purchase-orders
- POST /purchase-orders
Purpose: supplier and purchasing control domain.

6. Loyalty router (phase-ready): /api/v1/loyalty
- POST /members
- GET /members/{member_id}
- GET /campaigns
Purpose: Brasa Points member and campaign domain.

### API standards to apply across all routers
1. Versioned routes from day one to protect consumers from breaking changes.
2. Standard pagination and filtering conventions in list endpoints.
3. Consistent error envelope and machine-readable error codes.
4. Idempotency expectations for update/delete operations where applicable.
5. Explicit contract documentation for each route before new consumers integrate.

## 6. Domain Roadmap and Adoption Sequence

1. Wave 1: Talent Pipeline.
Stabilize current candidate and note lifecycle as the foundational domain.

2. Wave 2: Operations.
Add location performance and waste metrics domain aligned with decision-making needs.

3. Wave 3: Procurement.
Introduce supplier and purchasing context to reduce spreadsheet-heavy processes.

4. Wave 4: Marketing and Loyalty.
Evolve Brasa Points and campaign attribution into first-class backend capabilities.

Adoption guardrails:
- Keep API compatibility and version contracts stable across waves.
- Reuse shared cross-cutting modules instead of duplicating utilities.
- Define domain contracts before exposing endpoints to additional clients.

## 7. Risks and Points of Attention

1. Layer leakage risk.
If API, domain, and infrastructure concerns mix, changes become high-risk and slow. Impact: lower delivery speed, harder debugging, and fragile releases.

2. Domain boundary erosion risk.
If business rules are copied across modules, status/stage logic and eligibility rules drift. Impact: inconsistent behavior between routes and unreliable analytics.

3. Contract inconsistency risk.
If endpoints evolve without versioning and error standards, clients break unpredictably. Impact: backoffice instability and costly coordination.

4. Environment drift risk.
If configuration standards are not enforced per environment, staging and production behavior diverge. Impact: runtime incidents and unreliable incident triage.

## 8. Verification and Adoption Checklist

- The architecture pattern is justified with Brasaland-specific constraints.
- The backend structure is organized by clear layer responsibilities.
- FastAPI routers are grouped by domain and lifecycle ownership.
- Route standards define versioning, filtering, and error consistency.
- Risks describe concrete failure modes and operational impact.
- Domain roadmap provides phased adoption without architectural rewrites.
