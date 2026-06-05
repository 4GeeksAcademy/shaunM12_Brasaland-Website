# ARCHITECTURE PROPOSAL - Brasaland Backend

## 1. Objective and Scope

This document defines how Brasaland should structure the backend before implementation starts.

The goal is to provide a decision record that answers:
- What architecture we should adopt.
- Why it fits Brasaland's operating reality.
- How modules and domains should be organized.
- How FastAPI routes should be grouped for clarity and long-term maintainability.
- What risks we face if the structure is not followed.

In scope:
- Architectural pattern recommendation and trade-off analysis.
- Backend folder and module structure proposal.
- FastAPI endpoint and router organization by domain.
- Risks and operational points of attention.

Out of scope:
- Service implementation details.
- Data migration scripts.
- Infrastructure-as-code setup.
- Frontend refactors.

## 2. Business and Technical Context

Brasaland operates 14 restaurants across Colombia and the United States. The company is digitizing workflows that are currently fragmented across spreadsheets, email, and disconnected tools. The backend must support multiple domains that are related but distinct:
- Candidate pipeline management for people operations.
- Operations metrics (sales, waste, performance).
- Procurement workflows.
- Brasa Points loyalty management.

The frontends are separate systems (public website and internal backoffice). This means the backend must act as a stable contract layer, not as a UI-specific implementation detail.

Design implications:
- API contracts must remain stable while frontend experiences evolve independently.
- Business rules must live in backend domain logic, not duplicated in frontend code.
- Versioning and standardized errors are required from day one.

## 3. Architectural Decision

### 3.1 Recommended pattern

Domain-Oriented Layered Architecture implemented as a Modular Monolith using FastAPI.

### 3.2 Why this pattern fits Brasaland

1. Clear boundaries for a multi-domain company
- Brasaland has distinct business concerns with different owners and workflows.
- Domain-oriented modules reduce ambiguity about where rules belong.
- Consequence: faster onboarding and fewer cross-domain side effects.

2. Delivery speed without distributed-systems overhead
- The current scale does not require microservices-level operational complexity.
- A modular monolith provides separation and testability while keeping deployment simple.
- Consequence: faster iteration and lower DevOps burden in early backend phases.

3. Better control of business-critical consistency
- Revenue, margin, waste, and candidate lifecycle data influence business decisions.
- Layered boundaries make validation and business invariants explicit and auditable.
- Consequence: higher trust in data and lower risk of silent rule drift.

4. Strong fit with FastAPI capabilities
- FastAPI supports typed request/response models, async I/O, router composition, and contract-first API docs.
- Consequence: consistent interfaces for both website and backoffice clients.

### 3.3 Alternatives considered

1. MVC
- Benefit: simple mental model for small apps.
- Limitation: tends to couple transport logic and business logic as complexity grows.
- Decision: not selected as primary architecture.

2. Serverless-first
- Benefit: fast initial deployment and scaling primitives.
- Limitation: can fragment local development, tracing, and ownership boundaries for this stage.
- Decision: deferred until traffic and domain independence justify it.

3. Immediate microservices
- Benefit: strong service isolation.
- Limitation: high coordination cost, duplicated platform concerns, and slower early delivery.
- Decision: not selected for initial backend foundation.

## 4. Proposed Backend Module Structure

### 4.1 Structure overview

```text
backend/
	app/
		main.py
		api/
			routers/
				system.py
				candidates.py
				candidate_notes.py
				operations.py
				procurement.py
				loyalty.py
			schemas/
				common.py
				candidates.py
				operations.py
				procurement.py
				loyalty.py
		application/
			use_cases/
				candidates/
				operations/
				procurement/
				loyalty/
			services/
		domain/
			candidates/
				entities.py
				value_objects.py
				repository_ports.py
				policies.py
			operations/
			procurement/
			loyalty/
		infrastructure/
			persistence/
				sqlalchemy/
				repositories/
			external/
				email/
				analytics/
			security/
		shared/
			config/
			errors/
			logging/
			observability/
	tests/
		unit/
		integration/
		contract/
```

### 4.2 Responsibility separation criteria

1. API layer (app/api)
- Owns HTTP concerns only: parsing, validation at boundary, serialization, status codes, auth enforcement.
- Must not contain business decisions.

2. Application layer (app/application)
- Owns use-case orchestration: transactions, policy sequencing, command flow.
- Calls domain models and repository ports.

3. Domain layer (app/domain)
- Owns entities, value objects, invariants, and business policies.
- Must be framework-agnostic and persistence-agnostic.

4. Infrastructure layer (app/infrastructure)
- Owns adapters for databases, external services, and security implementations.
- Implements interfaces defined by domain/application layers.

5. Shared layer (app/shared)
- Owns cross-cutting concerns such as config, logging, structured errors, and observability.
- Must not become a dumping ground for domain logic.

6. Test layers
- Unit tests verify domain/application behavior.
- Integration tests verify API + infrastructure wiring.
- Contract tests verify request/response compatibility for frontend consumers.

### 4.3 Why this structure helps separate frontend and backend systems

- Frontends consume stable API contracts from the API layer.
- Backend can evolve internals (domain/application/infrastructure) without forcing frontend rewrites.
- Contract tests prevent accidental breaking changes when backend teams refactor internals.

## 5. FastAPI Endpoint and Router Organization by Domain

### 5.1 Grouping principles

1. Group by domain ownership, not by CRUD verb.
2. Keep aggregate and child resources close (for example, candidate and candidate notes).
3. Reserve system-level routes for platform concerns only.
4. Version all public APIs using /api/v1.

### 5.2 Proposed router map

1. System router
- Prefix: /api/v1/system
- Routes:
	- GET /health
	- GET /ready
	- GET /version
- Purpose: deployment/runtime checks for operations.

2. Candidates router
- Prefix: /api/v1/candidates
- Routes:
	- GET /
	- POST /
	- GET /{candidate_id}
	- PUT /{candidate_id}
	- PATCH /{candidate_id}
	- DELETE /{candidate_id}
- Purpose: candidate lifecycle ownership.

3. Candidate notes router
- Prefix: /api/v1/candidates/{candidate_id}/notes
- Routes:
	- GET /
	- POST /
	- DELETE /{note_id}
- Purpose: note lifecycle as child of candidate aggregate.

4. Operations router
- Prefix: /api/v1/operations
- Routes:
	- GET /locations
	- GET /locations/{location_id}/performance
	- GET /waste
	- GET /sales/summary
- Purpose: operational metrics and performance analytics.

5. Procurement router
- Prefix: /api/v1/procurement
- Routes:
	- GET /suppliers
	- GET /purchase-orders
	- POST /purchase-orders
	- PATCH /purchase-orders/{order_id}
- Purpose: supplier and order control workflows.

6. Loyalty router
- Prefix: /api/v1/loyalty
- Routes:
	- POST /members
	- GET /members/{member_id}
	- PATCH /members/{member_id}
	- GET /campaigns
- Purpose: Brasa Points member and campaign management.

### 5.3 API conventions that all routers must follow

1. Uniform list conventions
- Query params for pagination, filtering, sorting.
- Consistent metadata envelope for paginated results.

2. Uniform error model
- Machine-readable error code.
- Human-readable message.
- Correlation id for traceability.

3. Contract stability
- Backward-compatible changes within v1.
- Breaking changes require a new version path.

4. Auth and authorization boundaries
- Route-level role checks defined per domain.
- Sensitive operations (delete, status transitions) require explicit authorization policy.

## 6. Initial Technical Decisions (Day 0)

1. API contract-first workflow
- Define and review schema contracts before implementing handlers.
- Why: keeps frontend/backend teams aligned and reduces rework.

2. Dependency direction enforcement
- Domain cannot import FastAPI or ORM modules.
- Why: prevents long-term coupling and improves testability.

3. Unified configuration policy
- Environment-based settings with strict required variables in production.
- Why: prevents staging/production drift.

4. Structured observability baseline
- Request id propagation, structured logs, and basic metrics from first release.
- Why: production incidents become diagnosable without architectural rewrites.

5. Migration-ready persistence abstraction
- Use repository ports in domain/application layers from start.
- Why: allows future extraction to services if domain scale demands it.

## 7. Risks and Points of Attention

1. Layer leakage
- What can go wrong: business rules end up in routers or persistence adapters.
- Consequence: unpredictable behavior, hard refactors, high regression risk.
- Preventive control: architecture checks in review and dependency direction lint rules.

2. Domain boundary erosion
- What can go wrong: duplicated logic across candidates, loyalty, and operations modules.
- Consequence: inconsistent outcomes and low trust in analytics/reporting.
- Preventive control: single ownership per rule and domain policy review before merges.

3. API contract drift between teams
- What can go wrong: backend response changes without contract governance.
- Consequence: website/backoffice breakage and sprint delays.
- Preventive control: contract tests and required changelog for schema changes.

4. Premature microservice pressure
- What can go wrong: team splits services too early due to perceived scalability concerns.
- Consequence: slower delivery and operational complexity without business benefit.
- Preventive control: define objective extraction triggers (team size, throughput, scaling bottlenecks).

## 8. Team Alignment Notes (Confusion Prevention)

Potential confusion point 1: "Modular monolith" interpreted as "single folder with everything mixed"
- Clarification: modular monolith means one deployable unit with strict internal domain boundaries.

Potential confusion point 2: "FastAPI schema" interpreted as domain model
- Clarification: API schemas are transport contracts; domain entities are business models and may differ.

Potential confusion point 3: "Shared" interpreted as place for any reusable code
- Clarification: shared is only for cross-cutting technical concerns, never domain rules.

## 9. Phased Adoption Plan

1. Phase 1: Candidate lifecycle stabilization
- Complete candidate and notes domain with contract tests and role boundaries.

2. Phase 2: Operations metrics domain
- Add performance and waste endpoints with consistent filtering and reporting conventions.

3. Phase 3: Procurement workflows
- Introduce supplier and purchase order lifecycle with audit-ready status transitions.

4. Phase 4: Loyalty domain expansion
- Move Brasa Points membership and campaign operations to first-class backend modules.

Definition of done for each phase:
- Routes documented and versioned.
- Domain policies tested at unit level.
- Integration and contract tests passing.
- No cross-layer dependency violations introduced.

## 10. Final Recommendation

Brasaland should start with a domain-oriented layered modular monolith in FastAPI.

This provides the best balance of:
- business-rule clarity,
- delivery speed,
- low operational overhead,
- and migration readiness for future scale.

The proposal intentionally prioritizes explicit ownership boundaries and contract discipline so any team member can understand where logic belongs, why decisions were made, and what risks emerge if the structure is not respected.
