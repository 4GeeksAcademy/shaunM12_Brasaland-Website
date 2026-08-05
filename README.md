# Brasaland Website — AI Engineering Monorepo

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)

Brasaland transversal project for the **4Geeks Academy AI Engineering** program: FastAPI backend, Next.js public site and backoffice, shared TypeScript utilities, data pipelines, RAG, LangGraph agents, MCP tooling, and operational memory.

> Spanish instructions: [README.es.md](./README.es.md)

Business context: [CONTEXT.md](./CONTEXT.md)  
Agent protocol (Cursor/AI): [agents.md](./agents.md)  
Milestone 1 spec (website + Brasa Points): [context-1-milestone-1.md](./memory-bank/historical-reference/context-1-milestone-1.md)  
All milestone specs: [memory-bank/historical-reference/context-index.md](./memory-bank/historical-reference/context-index.md)

---

## Repository map

```text
├── services/api/       FastAPI — auth, inventory, incidents, telemetry, reporting, knowledge, agent
├── uis/website/        Public corporate site + Brasa Points registration (Milestone 1)
├── uis/backoffice/     Internal ops UI — inventory, incidents, reporting, knowledge, support (Milestones 3–8)
├── src/                Shared TypeScript business logic (Milestone 2)
├── packages/shared/    Shared Python helpers (e.g. restaurant location IDs)
├── mcps/               OAuth MCP servers — company-tools for incidents + inventory (Context 24)
├── data/               Datasets, pipeline code, RAG eval artifacts, agent checkpoint path (gitignored)
├── docs/               Design docs — RAG, pipelines, telemetry, forecasting, agent memory
├── scripts/            CLIs, nightly export, diagram render, serve helpers
├── agents/             Agent patterns (course scaffolding)
├── skills/             Reusable agent skills (course scaffolding)
└── memory-bank/        Milestone context files and working notes
```

| README | Scope |
| ------ | ----- |
| [services/api/README.md](./services/api/README.md) | API setup, env, endpoints, Celery, tests |
| [uis/backoffice/README.md](./uis/backoffice/README.md) | Backoffice routes, proxies, local dev |
| [uis/website/README.md](./uis/website/README.md) | Public website |
| [mcps/brasaland-company-tools/README.md](./mcps/brasaland-company-tools/README.md) | MCP OAuth server, Playground, agent bridge |
| [scripts/README.md](./scripts/README.md) | Nightly export, analyzer CLIs |

---

## Quick start

```bash
npm install
cp .env.example .env   # JWT_SECRET_KEY, DATABASE_URL, Qdrant, MCP, RAG keys — see template
npm run api:install
npm run api:dev          # http://127.0.0.1:8000
cd uis/backoffice && npm install && npm run dev   # http://localhost:3000
```

### Full stack — Support Agent (`/support`)

Needs **FastAPI**, **Qdrant**, **MCP**, and **Postgres** (`DATABASE_URL` for agent memory):

```bash
# Terminal 1 — API
npm run api:dev

# Terminal 2 — Backoffice
cd uis/backoffice && npm run dev

# Terminal 3 — MCP company-tools (incident reads/writes for agent)
npm run mcp:dev          # http://127.0.0.1:8765 — set MCPAUTH_REGISTRATION_SECRET in .env

# Terminal 4 — Qdrant (RAG context for agent + /knowledge)
docker compose up -d qdrant   # or local Qdrant on QDRANT_URL from .env.example
```

### Full stack — Knowledge Assistant (`/knowledge`)

API + Qdrant + backoffice (reindex via API or scripts; see [docs/rag/rag-design.md](./docs/rag/rag-design.md)).

### Async reporting pipeline (DEV-55)

Redis + Celery worker for `POST /reporting/pipeline-runs` — separate from nightly export ([context-18](./memory-bank/historical-reference/context-18-message-queues-async-tasks.md)):

```bash
docker compose up -d redis
cd services/api && uv run celery -A celery_app worker --loglevel=info
```

Docker Compose services: `backend`, `ui`, `redis`, `celery-worker`, `flower`, `nightly-worker`, `qdrant` — see [docker-compose.yml](./docker-compose.yml).

---

## Backoffice routes (implemented)

| Route | Feature | Milestone / context |
| ----- | ------- | ------------------- |
| `/` | Dashboard | Milestone 3–4 |
| `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email` | Auth flows | [context-7](./memory-bank/historical-reference/context-7-authentication-and-route-restriction.md), [context-8](./memory-bank/historical-reference/context-8-authentication-flows-frontend.md) |
| `/incidents`, `/incidents/[id]` | Centralized incident manager | [context-13](./memory-bank/historical-reference/context-13-centralized-incident-manager.md) |
| `/suppliers` | Supplier directory | [context-6](./memory-bank/historical-reference/context-6-supplier-directory.md) |
| `/inventory/*` | Products, inbound/outbound orders | [context-11](./memory-bank/historical-reference/context-11-milestone-5-backend-inventory-management.md), [context-12](./memory-bank/historical-reference/context-12-milestone-5-backoffice-inventory-interface.md) |
| `/reporting` | Weekly KPIs + manual pipeline trigger | [context-16](./memory-bank/historical-reference/context-16-milestone-6-data-pipeline-design.md), Celery [context-18](./memory-bank/historical-reference/context-18-message-queues-async-tasks.md) |
| `/registration-analytics` | Brasa Points registration analytics | Milestone 1 |
| `/data-processing` | Incident file analyzer UI | [context-5](./memory-bank/historical-reference/context-5-incident-file-analyzer.md) |
| `/candidates/[id]` | HR candidate detail (demo) | Milestone 3–4 |
| `/knowledge` | RAG knowledge assistant | [context-21](./memory-bank/historical-reference/context-21-rag-knowledge-base.md) |
| `/support` | LangGraph support agent + memory coaching | [context-23](./memory-bank/historical-reference/context-23-support-agent-langgraph-p1.md)–[26](./memory-bank/historical-reference/context-26-milestone-8-agent-memory.md) |

Route/proxy conventions: [context-22](./memory-bank/historical-reference/context-22-route-conventions.md).

---

## Deliverables by milestone

Status reflects work merged into this repo through **Milestone 8**. Milestones **9–10** (workflows, real-time) are the remaining course scope.

| Milestone | Status | Summary | Key paths / specs |
| --------- | ------ | ------- | ----------------- |
| **0** | Done | Dev environment, monorepo tooling | Root `package.json`, `.env.example` |
| **1** | Done | Corporate website + Brasa Points registration | `uis/website/`, [qa-checklist-milestone-1.md](./docs/qa-checklist-milestone-1.md) |
| **2** | Done | Shared TypeScript business logic | `src/`, `npm run typecheck`, `npm test` |
| **3–4** | Done | Backoffice Next.js ops shell | `uis/backoffice/` |
| **5** | Done | Backend — auth, suppliers, inventory, incidents | `services/api/`, contexts 6–7, 11–13 |
| **6** | Done | Telemetry capture, Prefect pipeline, reporting APIs + UI | `services/api/telemetry/`, `reporting/`, [PIPELINE_DESIGN.md](./docs/pipelines/PIPELINE_DESIGN.md), contexts 15–16 |
| **7** | Done | RAG knowledge base — Qdrant, embed, retrieve, `/knowledge` | `services/api/knowledge/`, `docs/rag/`, `docs/company-knowledge-base/`, [context-21](./memory-bank/historical-reference/context-21-rag-knowledge-base.md) |
| **8** | Done | Agent memory (MEM-092) — propose, confirm, audit, inject | `services/api/agent/memory/`, [memory-design.md](./docs/agent/memory-design.md), [context-26](./memory-bank/historical-reference/context-26-milestone-8-agent-memory.md) |
| **9–10** | Planned | Workflows, real-time (course) | `agents/`, `skills/` scaffolding |

### Cross-cutting workstreams (also shipped)

| Workstream | What it adds | Spec |
| ---------- | ------------ | ---- |
| **Error handling** | API error shapes, backoffice display | [context-9](./memory-bank/historical-reference/context-9-error-handling.md) |
| **Unit testing** | API + UI test suites | [context-10](./memory-bank/historical-reference/context-10-unit-testing.md) |
| **Containerization** | Docker Compose stack | [context-14](./memory-bank/historical-reference/context-14-containerization.md) |
| **Nightly export (DEV-53)** | Telemetry export + pipeline trigger script | [context-17](./memory-bank/historical-reference/context-17-background-processes-nightly-telemetry.md), `npm run api:nightly-export` |
| **Sales forecasting** | Random Forest on consolidated sales CSV | [context-19](./memory-bank/historical-reference/context-19-sales-forecasting-regression.md), [docs/forecasting/](./docs/forecasting/) |
| **Model evaluation** | Learning curve, walk-forward CV, report | [context-20](./memory-bank/historical-reference/context-20-evaluating-regression-model.md) |

### Agent stack (Milestones 7–8 + SEC/MCP)

Built incrementally on `/agent/query` and `/support`:

| Layer | Deliverable | Spec |
| ----- | ----------- | ---- |
| **LangGraph P1** | Graph migration, SQLite checkpoint, `POST /agent/query`, `/support` UI | [context-23 P1](./memory-bank/historical-reference/context-23-support-agent-langgraph-p1.md) |
| **LangGraph P2** | Rule-based classifier, incident/inventory tools, routing evals | [context-23 P2](./memory-bank/historical-reference/context-23-support-agent-langgraph-p2.md) |
| **MCP company-tools** | OAuth MCP server; agent incidents via MCP | [context-24](./memory-bank/historical-reference/context-24-mcp-company-tools.md), `mcps/brasaland-company-tools/` |
| **Guardrails (SEC-114)** | Input/content/security layers, output validation, observability | [context-25](./memory-bank/historical-reference/context-25-securing-agents-harness-guardrails.md) |
| **Agent memory (MEM-092)** | Postgres episodic store, two-turn propose→confirm, denylist, evidence cycles A–D | [context-26](./memory-bank/historical-reference/context-26-milestone-8-agent-memory.md) |

**Memory architecture (short):** Postgres `agent_memory_entries` + audit log; pending proposals in LangGraph checkpoint (`thread_id` on request); explicit `read_memory()` / `write_memory()` — not vector memory, not chat log. `/knowledge/query` unchanged.

**New in Milestone 8 (representative paths):**

- `services/api/agent/memory/` — store, classifier, denylist, proposal inference, location hints  
- `docs/agent/memory-design.md`, `docs/agent/memory-evidence.md`  
- `uis/backoffice/lib/support-memory-coaching.ts` — approve-phrase UI on `/support`  
- Tests: `services/api/tests/pipelines/test_agent_memory*.py`

---

## API surface (high level)

| Prefix | Purpose |
| ------ | ------- |
| `/auth`, `/users` | JWT auth, password reset |
| `/suppliers` | Supplier directory (TinyDB) |
| `/incidents` | CRUD, analyze, export |
| `/inventory` | Products and stock orders (Postgres) |
| `/telemetry` | Event ingest + on-demand report |
| `/reporting` | Weekly KPIs; `POST /reporting/pipeline-runs` → Celery |
| `/tasks/{task_id}` | Async task status |
| `/knowledge/query`, `/knowledge/reindex` | RAG (Qdrant) |
| `/agent/query` | LangGraph support agent (optional `thread_id` for memory) |

Detail: [services/api/README.md](./services/api/README.md).

---

## Design documentation

| Doc | Topic |
| --- | ----- |
| [agents.md](./agents.md) | Agent operating protocol (context triggers, protected paths, pre-commit) |
| [docs/rag/rag-design.md](./docs/rag/rag-design.md) | RAG architecture, indexing, retrieval |
| [docs/agent/memory-design.md](./docs/agent/memory-design.md) | Agent memory Q1–Q5, denylist, lifecycle |
| [docs/agent/memory-evidence.md](./docs/agent/memory-evidence.md) | Evidence cycles A–D |
| [docs/pipelines/PIPELINE_DESIGN.md](./docs/pipelines/PIPELINE_DESIGN.md) | Milestone 6 ETL / Prefect pipeline |
| [docs/telemetry/telemetry-plan.md](./docs/telemetry/telemetry-plan.md) | Telemetry schemas and KPIs |
| [docs/forecasting/README.md](./docs/forecasting/README.md) | Sales forecast notebook + metrics |
| [docs/diagrams/mermaid/](./docs/diagrams/mermaid/) | Architecture diagrams (RAG, support agent, pipeline) |

---

## Testing

```bash
# Shared TypeScript (Milestone 2)
npm run typecheck && npm test

# API (includes memory, agent, guardrails, RAG pipelines)
npm run api:test

# Agent memory regression gate (MEM-092)
cd services/api && uv run pytest tests/pipelines/test_agent_memory*.py tests/test_agent_api.py -q

# MCP server
npm run mcp:test

# Backoffice
cd uis/backoffice && npm test
```

---

## Root npm scripts (reference)

| Script | Action |
| ------ | ------ |
| `npm run api:dev` | FastAPI on `:8000` |
| `npm run api:seed` / `api:inventory-seed` / `api:incidents-seed` / `api:telemetry-seed` | Demo data |
| `npm run mcp:dev` | MCP company-tools on `:8765` |
| `npm run api:nightly-export` | DEV-53 nightly telemetry export |
| `npm run diagrams:render` | Render Mermaid diagrams under `docs/diagrams/` |

---

## Links

- [4Geeks Academy — AI Engineering](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [How to start a coding project](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contributors

Template lineage from the 4Geeks Academy AI Engineering program ([@marcogonzalo](https://www.linkedin.com/in/marcogonzalo), [@alezanchezr](https://x.com/alesanchezr), and contributors).  
[AI Engineering Course](https://4geeksacademy.com/en/career-programs/ai-engineering) · [GitHub org](https://github.com/4geeksacademy)
