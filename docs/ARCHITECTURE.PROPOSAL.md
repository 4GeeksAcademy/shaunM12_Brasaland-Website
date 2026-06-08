# ARCHITECTURE.PROPOSAL.md

## 1. Context and Scope

Brasaland operates 14 restaurants across Colombia and the United States. The business has strong growth potential, but many internal processes remain fragmented across spreadsheets, email, and messaging tools. This creates slow decisions, reporting gaps, and inconsistent operational visibility.

This proposal defines a backend architecture direction that supports Brasaland Digital's next stage: centralizing core business processes behind reliable APIs while keeping delivery speed high for a small-to-medium engineering footprint.

Scope of this proposal:
- Select and justify the most suitable architectural pattern for Brasaland.
- Propose a backend folder and module structure with clear separation criteria.
- Describe how FastAPI endpoints and routers should be organized by domain.
- Identify risks if the architecture is not followed.

Out of scope:
- Detailed code implementation.
- Database migration scripts.
- Infrastructure provisioning details.

## 2. Recommended Architectural Pattern

### Decision

Use a **Domain-Oriented Layered Modular Monolith** implemented with FastAPI.

### Why this is the best fit for Brasaland

1. Multi-country operations need clear boundaries.
Brasaland runs in Colombia and the US with different operational contexts, but shared business rules. Domain boundaries reduce ambiguity and keep logic consistent across markets.

2. Current scale does not justify microservices yet.
Brasaland has meaningful complexity but not enough service-scale pressure to offset microservice overhead. A modular monolith gives strong structure without distributed-system coordination costs.

3. Fast delivery is a business requirement.
The company needs operational digitization now. A single deployable backend with strong module boundaries allows faster implementation and easier onboarding.

4. Data trust is critical for decisions.
Leadership currently suffers from delayed, fragmented reporting. A layered design keeps business rules centralized and testable, improving confidence in KPIs.

5. Existing repository direction already favors governance.
Current project constraints emphasize type safety, shared validation, and environment-first configuration. A layered modular monolith aligns naturally with those rules.

### Alternatives considered

1. MVC
- Pros: Simple to start.
- Cons: For Brasaland, MVC often blurs domain logic with transport concerns as complexity grows.

2. Serverless-first architecture
- Pros: Elastic scaling and managed runtime.
- Cons: At current stage, it can fragment ownership, increase operational complexity, and make cross-domain debugging harder.

3. Early microservices
- Pros: Independent scaling and team autonomy.
- Cons: High coordination overhead, contract management burden, and observability complexity before Brasaland has enough backend domain maturity.

## 3. Proposed Backend Structure (Folders and Modules)

Suggested project structure:

```text
backend/
  app/
    main.py
    startup.py
  api/
    routers/
      candidates.py
      candidate_notes.py
      operations.py
      procurement.py
      loyalty.py
      health.py
    schemas/
      candidates.py
      notes.py
      operations.py
      procurement.py
      loyalty.py
    dependencies/
      auth.py
      pagination.py
      request_context.py
  application/
    candidates/
      use_cases/
        create_candidate.py
        update_candidate_status.py
        replace_candidate.py
        delete_candidate.py
      services/
        candidate_service.py
    operations/
      use_cases/
      services/
    procurement/
      use_cases/
      services/
    loyalty/
      use_cases/
      services/
  domain/
    candidates/
      entities.py
      value_objects.py
      rules.py
      repository_contracts.py
    operations/
      entities.py
      rules.py
      repository_contracts.py
    procurement/
      entities.py
      rules.py
      repository_contracts.py
    loyalty/
      entities.py
      rules.py
      repository_contracts.py
    shared/
      errors.py
      events.py
  infrastructure/
    persistence/
      models/
      repositories/
      unit_of_work.py
    external/
      notification_client.py
      analytics_client.py
    config/
      settings.py
    logging/
      logger.py
  tests/
    unit/
      domain/
      application/
    integration/
      api/
    contract/
      consumers/
```

### Responsibility separation criteria

1. API layer
- Owns HTTP transport concerns only.
- Converts request/response payloads to application commands and results.
- Must not contain core business decisions.

2. Application layer
- Orchestrates use cases.
- Coordinates domain services, repositories, and transactions.
- Contains workflow logic, not framework details.

3. Domain layer
- Owns business rules and invariants.
- Defines entities, value objects, and domain contracts.
- Must be independent from FastAPI and database tooling.

4. Infrastructure layer
- Implements technical adapters (DB, external APIs, message providers).
- Fulfills interfaces defined by the domain/application layers.
- Must not introduce business rules.

5. Shared cross-cutting modules
- Include config, auth helpers, logging, error mapping, and request context.
- Must remain generic and reusable; no hidden domain-specific behavior.

## 4. FastAPI Endpoint and Router Organization by Domain

### Grouping criteria

Routers should be grouped by bounded context and resource ownership, not by HTTP method or technical utility.

Grouping rules:
1. Routes belong to the domain that owns the lifecycle of the data.
2. Nested resources stay with their parent aggregate domain.
3. Cross-domain operations should be implemented as explicit orchestration use cases.

### Suggested route groups

Base prefix:
- `/api/v1`

1. Candidate Pipeline Domain (current tracker foundation)
- `GET /api/v1/candidates`
- `POST /api/v1/candidates`
- `GET /api/v1/candidates/{candidate_id}`
- `PUT /api/v1/candidates/{candidate_id}`
- `PATCH /api/v1/candidates/{candidate_id}`
- `DELETE /api/v1/candidates/{candidate_id}`
- `GET /api/v1/candidates/{candidate_id}/notes`
- `POST /api/v1/candidates/{candidate_id}/notes`
- `DELETE /api/v1/candidates/{candidate_id}/notes/{note_id}`

2. Operations Domain
- `GET /api/v1/operations/locations`
- `GET /api/v1/operations/locations/{location_id}/performance`
- `GET /api/v1/operations/locations/{location_id}/waste`
- `POST /api/v1/operations/locations/{location_id}/waste`
- `GET /api/v1/operations/reports/daily`
- `GET /api/v1/operations/reports/country-comparison`

3. Procurement Domain
- `GET /api/v1/procurement/suppliers`
- `POST /api/v1/procurement/purchase-orders`
- `GET /api/v1/procurement/purchase-orders`
- `GET /api/v1/procurement/purchase-orders/{order_id}`
- `PATCH /api/v1/procurement/purchase-orders/{order_id}`

4. Loyalty and Marketing Domain
- `POST /api/v1/loyalty/registrations`
- `GET /api/v1/loyalty/members/{member_id}`
- `PATCH /api/v1/loyalty/members/{member_id}/preferences`
- `GET /api/v1/loyalty/reports/attribution`

5. Platform and System
- `GET /api/v1/health`
- `GET /api/v1/readiness`

### Endpoint standards

1. Versioning
- All external routes use explicit versioning (`/api/v1`).

2. Pagination and filtering
- List endpoints should support consistent query conventions (`page`, `limit`, `sort`, domain-specific filters).

3. Error envelope
- Use a uniform error response structure for all domains.

4. Idempotency
- `PUT` should be idempotent replacement.
- `PATCH` should be partial updates with deterministic conflict handling.
- `DELETE` should return a predictable response for already-removed resources.

## 5. Domain Roadmap and Adoption Sequence

To reduce risk and preserve delivery velocity, implementation should follow a phased domain rollout.

1. Wave 1: Candidate Pipeline Domain
- Consolidate and harden existing tracker behavior.
- Establish baseline conventions for schemas, error handling, pagination, and tests.

2. Wave 2: Operations Domain
- Add performance and waste reporting endpoints.
- Centralize location-level KPI logic to reduce spreadsheet dependency.

3. Wave 3: Procurement Domain
- Add supplier and purchase-order flows.
- Create consistent procurement visibility and lifecycle tracking.

4. Wave 4: Loyalty and Marketing Domain
- Extend Brasa Points data capture and analytics endpoints.
- Enable campaign attribution and customer insight pipelines.

Adoption guardrails for every wave:
- Preserve backwards compatibility for existing clients.
- Publish and validate contracts before onboarding new consumers.
- Reuse shared cross-cutting modules instead of duplicating concerns.

## 6. Risks and Points of Attention

1. Layer leakage risk
If business rules are implemented inside routers or infrastructure adapters, behavior will become inconsistent and fragile. Impact: slower change cycles, hard-to-test logic, and higher defect rates.

2. Domain boundary erosion
If teams place cross-domain logic in arbitrary modules, data ownership becomes unclear. Impact: conflicting status/stage rules, duplicated validations, and reporting drift.

3. API inconsistency risk
Without route/version standards, clients will integrate against unstable contracts. Impact: frontend breakages and high maintenance cost.

4. Environment and configuration drift
If environment-first configuration is not enforced, staging and production can silently diverge. Impact: runtime failures and difficult incident diagnosis.

5. Premature service fragmentation
If the team moves too early to microservices without domain maturity, operational overhead can exceed delivery value. Impact: slower roadmap execution and increased platform burden.

## 7. Verification and Adoption Checklist

Before each major backend increment, verify:

- Architectural boundaries are respected (API, application, domain, infrastructure).
- New routes are added under the correct domain router group.
- Shared concerns are centralized (auth, config, logging, error handling).
- Domain contracts are explicit and tested.
- Existing client contracts remain compatible or are versioned intentionally.
- Environment variables are explicitly defined for target environments.
- Integration and contract tests cover changed workflows.

## 8. Final Recommendation

Brasaland should adopt a FastAPI-based Domain-Oriented Layered Modular Monolith now, with phased domain expansion. This architecture gives the best balance of speed, maintainability, and business reliability for a two-country restaurant chain modernizing from fragmented manual processes to a unified digital operating model.
