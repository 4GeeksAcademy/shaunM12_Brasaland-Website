# AI Engineering Company Project — Student Template

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)

_Base template for transversal projects in the AI Engineering Career Program — 4Geeks Academy._

> _Instrucciones disponibles en español en [README.es.md](./README.es.md)._

---

## Purpose

This repository is the **starter template** for transversal projects. You will work on real company scenarios (Brasaland, TrackFlow, Nexova), building deliverables that map to course milestones (Web, Programming, Backend, Telemetry, RAG, Agents, Workflows, Real-time).

- Create a template from this repository.
- Replace the placeholder `CONTEXT.md` with your assigned company context.
- Use `skills/` and the directory-level `README.md` files as working guidance.

---

## Repository structure

```text
brasaland-website/
├── README.md
├── README.es.md
├── CONTEXT.md                # Brasaland business context
├── package.json             # Root tooling (TypeScript utils, scripts, tests)
├── services/
│   └── api/                  # FastAPI backend (auth, suppliers, incidents, mailer)
├── uis/
│   ├── backoffice/           # Next.js internal operations app
│   └── website/              # Next.js public website
├── src/                      # Shared TypeScript utilities (types + data helpers)
├── tests/                    # Tests for src/ utilities
├── scripts/                  # Node + Python tooling (CLIs, data generation)
├── data/                     # Datasets (incident CSVs, etc.)
├── agents/                   # Agent patterns/templates and tools docs
├── docs/                     # Project and architecture documentation
└── skills/                   # Reusable agent skills
```

---

## How to start

1. **Clone** your repository (or open it in Codespaces).
2. **Install** root dependencies with `npm install`; backend deps with `npm run api:install`.
3. **Review** each top-level folder `README.md` to understand intended responsibilities.
4. **Run** the backend (`npm run api:dev`) and a frontend (`cd uis/backoffice && npm run dev`).

---

## Milestones (reference)

| Milestone | Focus        | Typical deliverables                        |
| --------- | ------------ | ------------------------------------------- |
| 0         | Prework      | Environment setup, first prompts            |
| 1         | Web          | Corporate website, forms, SEO               |
| 2         | Programming  | Business logic, scoring, calculations       |
| 3         | AI-driven UI | AI-generated interfaces                     |
| 4         | Next.js      | Portals, loyalty app, operations UI         |
| 5         | Backend      | Central API (locations, menus, sales, etc.) |
| 6         | Telemetry    | Data pipeline, dashboards                   |
| 7         | RAG & Memory | Semantic knowledge base, search             |
| 8         | Agents       | Support, onboarding, training agents        |
| 9         | Workflows    | n8n automations                             |
| 10        | Real-time    | Live dashboards, alerts, streaming          |

---

## Milestone 2 implementation (Programming Fundamentals)

This repository now includes a TypeScript implementation for Milestone 2 under `src/`:

```text
src/
├── demo.ts
├── index.ts
├── index.html
├── types/
│   └── models.ts
└── utils/
	├── collections.ts
	├── search.ts
	├── transformations.ts
	└── validations.ts
```

Automated tests are located in `tests/`.

### Development commands

```bash
npm install
npm run typecheck
npm test
npm run demo
npm start
npm run serve
npm run serve:src
npm run serve:root
npm run serve:required
npm run serve:logs
npm run serve:stop
```

`npm run serve` serves the site from the repository root (detached mode).
`npm run serve:src` serves the operations interface from `src/` directly (detached mode).
`npm run serve:root` serves the repository root (detached mode).
`npm run serve:required` runs the exact required command: `npx http-server . -p 3000 -a 0.0.0.0`.
`npm run serve:logs` shows recent server log output.
`npm run serve:stop` stops the detached server.
If you typed `npm serve run`, that command is invalid and will not start the server.

Migration note: the legacy folder `Brasaland webpage/` has been retired. The TypeScript implementation now lives under `src/`.

These commands satisfy the requirement to expose a clear TypeScript validation/execution workflow during development.

---

## Links

- [4Geeks Academy — AI Engineering](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [How to start a coding project](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contributors

This template was built as part of the 4Geeks Academy AI Engineering Career Program by [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo) and [@alezanchezr](https://x.com/alesanchezr) and many other contributors. Find out more about our [AI Engineering Course](https://4geeksacademy.com/en/career-programs/ai-engineering), and [other courses](https://4geeksacademy.com/en/program-comparison).

You can find other templates and resources like this at the [4Geeks Academy GitHub page](https://github.com/4geeksacademy).

_This template is maintained by 4Geeks Academy for the AI Engineering track. For exclusive use in the programme._
