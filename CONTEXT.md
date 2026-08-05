# CONTEXT.md — Brasaland

> **Single source of truth** for company identity, operating context, and cross-cutting domain facts across this monorepo. Milestone-specific build specs live under [`memory-bank/historical-reference/`](memory-bank/historical-reference/context-index.md).

---

## Purpose

**Brasaland** is the fictional company scenario for the **4Geeks Academy AI Engineering** transversal project. **Brasaland Digital** is the internal transformation team modernizing operations across Colombia and the United States.

This repository implements the full digital platform: public website, backoffice, FastAPI services, data pipelines, RAG, LangGraph agents, and MCP tooling. Root `CONTEXT.md` describes the company and domain constants that apply everywhere; individual milestones have their own spec files (see [Document map](#document-map)).

---

## Company identity

**Brasaland** is a grilled food restaurant chain founded in **2008** in Medellín, Colombia. What began as a single family-run location is now **14 company-owned restaurants** in Colombia and the United States (Florida and surrounding markets). The company employs approximately **115 people** and generates around **6 million USD** in annual revenue.

**Brand pillars:**

- Consistent product quality in every location
- Warm, reliable customer experience
- Speed of service without sacrificing quality

**Leadership:**

- **CEO:** Mariana Restrepo (Medellín headquarters)
- **CTO:** Nicolás Park — leads Brasaland Digital
- **Commercial office:** Miami

---

## Operating context and current problems

Brasaland remains profitable, but many critical processes are still manual (spreadsheets, email, WhatsApp, disconnected systems). This creates visibility gaps and slower decision-making across two countries.

### Restaurant operations

**Lead:** Felipe Guerrero

- Locations operate with limited real-time visibility
- Ingredient ordering is mostly manual
- Reporting is fragmented and delayed

### Procurement and suppliers

**Lead:** Lucia Fernandez

- Around 20 suppliers across both markets
- Negotiation and tracking rely on email and spreadsheets
- No consolidated purchasing intelligence

### Marketing and digital experience

**Lead:** Camila Ospina

- Website was outdated and lacked modern conversion flows (addressed in Milestone 1)
- Loyalty program was physical-card based and generated little data (Brasa Points in Milestone 1)
- Minimal customer-level insight

### People and culture

**Lead:** Ashley Turner

- HR processes are mostly manual
- Two-country labor context increases operational complexity

### Training and quality standards

**Lead:** Jake Morrison

- Training material distribution is hard to maintain
- Update communication is slow across locations and countries

### Technology

**Lead:** CTO Nicolás Park

- Shared FastAPI platform, backoffice, pipelines, RAG, and agents (this monorepo)
- Unified internal API and growing telemetry integration

### Executive direction

**Lead:** CEO Mariana Restrepo

- Strategic decisions were delayed by fragmented reporting
- Centralized, near real-time business view is an ongoing goal (telemetry, reporting, forecasting)

---

## Digital platform (this repository)

| Area | Path | Spec pointer |
| --- | --- | --- |
| Public site + Brasa Points | `uis/website/` | [`context-1-milestone-1.md`](memory-bank/historical-reference/context-1-milestone-1.md) |
| Shared TypeScript business logic | `src/` | [`context-2-milestone-2.md`](memory-bank/historical-reference/context-2-milestone-2.md) |
| Backoffice ops UI | `uis/backoffice/` | contexts 3, 5, 12, and related |
| FastAPI service | `services/api/` | contexts 6–8, 11, 13, 15–18, 21, 23 |
| Shared Python helpers | `packages/shared/` | location IDs, cross-service constants |
| Data pipelines / forecasting | `data/` | contexts 16, 19–20 |
| RAG / knowledge assistant | `/knowledge` | [`context-21-rag-knowledge-base.md`](memory-bank/historical-reference/context-21-rag-knowledge-base.md) |
| Support agent | `/support`, `/agent` | contexts 23, 25, 26 |
| MCP company tools | `mcps/` | [`context-24-mcp-company-tools.md`](memory-bank/historical-reference/context-24-mcp-company-tools.md) |

Full index: [`memory-bank/historical-reference/context-index.md`](memory-bank/historical-reference/context-index.md)

---

## Cross-cutting domain constants

### Restaurant locations (authoritative)

**14 locations, IDs 1–14.** Use these sources — not ad-hoc lists:

| Layer | Source |
| --- | --- |
| Python (API, inventory, agent) | `packages/shared/restaurant_locations.py` |
| Website form and filters | `uis/website/lib/restaurant-locations.ts` |

IDs 1–7 are Colombia; 8–14 are United States. City and name strings in code supersede course marketing copy in milestone specs when they differ.

### Brasa Points (loyalty program)

- For **customers aged 18+** who earn points from restaurant visits
- **Not** online ordering or reservations
- Points rule: 1 point per **$10,000 COP** or **$5 USD** spent
- Form fields, validations, and UX copy: [`context-1-milestone-1.md`](memory-bank/historical-reference/context-1-milestone-1.md)

### Contact and markets

- **Email:** hello@brasaland.com
- **Colombia phone:** +57 4 123 4567
- **Florida phone:** +1 305 123 4567
- **Countries of operation:** Colombia (CO), United States (US)

### Agent and RAG company knowledge

Support agent and knowledge-base answers draw from **`docs/company-knowledge-base/`** and RAG corpus per context-21 — not Milestone 1 marketing landing copy.

---

## Document map

| Question | Read first |
| --- | --- |
| Company identity, departments, domain facts | **CONTEXT.md** (this file) |
| AI agent protocol (Cursor), protected paths, triggers | [`agents.md`](../agents.md) |
| Stack, routes, env vars, local commands | [`memory-bank/techContext.md`](memory-bank/techContext.md) |
| Milestone 1 website / Brasa Points form | [`context-1-milestone-1.md`](memory-bank/historical-reference/context-1-milestone-1.md) |
| Named milestone or feature | Developer-named `context-{n}-*.md` file |
| Route/proxy conventions | [`context-22-route-conventions.md`](memory-bank/historical-reference/context-22-route-conventions.md) |
| Implementation status | [`memory-bank/progress.md`](memory-bank/progress.md) |

**Precedence:** live code wins over docs on conflict; flag drift to the developer. Historical-reference files are milestone specs — consult the one relevant to your task, not the whole directory.

---

## What belongs elsewhere

- **Milestone 1 landing sections, form table, error messages, Schema.org** → `context-1-milestone-1.md`
- **FastAPI mounts, backoffice proxies, camelCase/snake_case** → `techContext.md` + `context-22-route-conventions.md`
- **Engineering rules and CI gates** → [`agents.md`](../agents.md) + [`.agents/rules/LEGACY_INDEX.md`](../.agents/rules/LEGACY_INDEX.md)
- **Session progress and changelog** → `memory-bank/progress.md`
