# Brasaland Website — AI Engineering Monorepo

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)

Brasaland transversal project for the **4Geeks Academy AI Engineering** program: FastAPI backend, Next.js public site and backoffice, shared TypeScript utilities, data pipelines, and agent tooling.

> Spanish instructions: [README.es.md](./README.es.md)

---

## Purpose

Build deliverables for Brasaland company scenarios across course milestones (Web, Programming, Backend, Telemetry, RAG, Agents, Workflows, Real-time).

Business context: [CONTEXT.md](./CONTEXT.md)  
Historical milestone notes: [memory-bank/historical-reference/context-index.md](./memory-bank/historical-reference/context-index.md)

---

## Repository map

```text
├── services/api/     FastAPI backend (auth, inventory, incidents, telemetry, reporting)
├── uis/              Next.js apps (website + backoffice)
├── src/              Shared TypeScript utilities (Milestone 2)
├── scripts/          CLIs, nightly export, data helpers
├── data/             Datasets, pipeline transforms, raw/eval artifacts
├── docs/             Architecture and design docs
├── agents/           Agent patterns and tools
├── skills/           Reusable agent skills
├── packages/shared/  Shared Python validation helpers
└── memory-bank/      Working notes and historical context files
```

Details live next to each area — use the documentation map below.

---

## Quick start

```bash
# Root tooling
npm install
cp .env.example .env   # set JWT_SECRET_KEY and other secrets

# Backend (http://127.0.0.1:8000)
npm run api:install
npm run api:dev

# Backoffice (http://localhost:3000) — second terminal
cd uis/backoffice && npm install && npm run dev
```

Public site: `cd uis/website && npm install && npm run dev`  
Docker Compose: see `docker-compose.yml` (`backend`, `ui`, `nightly-worker`).

---

## Documentation map

| Area | README | What you’ll find there |
| ---- | ------ | ---------------------- |
| API | [services/api/README.md](./services/api/README.md) | Setup, env, auth, seeds, endpoints, tests |
| UIs (index) | [uis/README.md](./uis/README.md) | Apps in this folder |
| Public website | [uis/website/README.md](./uis/website/README.md) | Next.js corporate site |
| Backoffice | [uis/backoffice/README.md](./uis/backoffice/README.md) | Ops UI, proxies, env |
| Scripts | [scripts/README.md](./scripts/README.md) | Analyzer, nightly export/scheduler |
| Docs | [docs/README.md](./docs/README.md) | Pipeline & telemetry design links |
| Agents | [agents/README.md](./agents/README.md) | Agent templates catalog |
| Skills | [skills/README.md](./skills/README.md) | Agent skills catalog |

Shared TypeScript (`src/`) commands: `npm run typecheck`, `npm test`, `npm run demo`.  
Root serve helpers: `npm run serve` / `serve:src` / `serve:stop` (see `package.json`).

---

## Milestones (reference)

| Milestone | Focus | Typical deliverables |
| --------- | ----- | -------------------- |
| 0 | Prework | Environment setup |
| 1 | Web | Corporate website |
| 2 | Programming | Business logic under `src/` |
| 3–4 | UI / Next.js | Portals and ops UI under `uis/` |
| 5 | Backend | API under `services/api/` |
| 6 | Telemetry / pipeline | Telemetry, reporting, Prefect pipeline |
| 7–10 | RAG, agents, workflows, real-time | Agents, skills, further automation |

---

## Links

- [4Geeks Academy — AI Engineering](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [How to start a coding project](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contributors

Template lineage from the 4Geeks Academy AI Engineering program ([@marcogonzalo](https://www.linkedin.com/in/marcogonzalo), [@alezanchezr](https://x.com/alesanchezr), and contributors).  
[AI Engineering Course](https://4geeksacademy.com/en/career-programs/ai-engineering) · [GitHub org](https://github.com/4geeksacademy)
