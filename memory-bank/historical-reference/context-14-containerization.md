# CONTEXT — Repository Containerization for Development · Brasaland

## AI Engineering - 4Geeks Academy

> **Ticket:** INFRA-40 — Dockerize full monorepo development stack  
> **Repository index:** `context-14-containerization.md`  
> **Type:** Infrastructure / developer experience  
> **Status:** Implemented baseline (Docker + Compose + root `.env` wiring)

---

## Locked Decisions

- Single UI container runs both `uis/website` and `uis/backoffice`.
- Hot reload is required for UI and backend in dev.
- `docker compose up` from repo root is the entrypoint.
- Inter-service traffic uses service names (never container `localhost`).
- Config is environment-driven from root `.env`.
- No real secrets in Dockerfiles or compose files.

---

## Focus

Brasaland needs deterministic local development: clone, configure `.env`, run one compose command, and start coding without host drift.

Containerized scope:

- `uis/website` (Next.js, dev mode)
- `uis/backoffice` (Next.js, dev mode)
- `services/api` (FastAPI, reload mode)

---

## Scope

### In scope

- `uis/Dockerfile`, `uis/start.sh`, `uis/.dockerignore`
- `services/Dockerfile`, `services/.dockerignore`
- root `docker-compose.yml`
- root `.env` as shared runtime source
- bind mounts for live reload
- named network for service-name communication

### Out of scope

- production hardening
- CI/CD deployment automation
- enterprise secret management

---

## Required File Layout

```text
/
├── .env
├── .env.example
├── docker-compose.yml
├── uis/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── start.sh
│   ├── website/
│   └── backoffice/
└── services/
    ├── Dockerfile
    ├── .dockerignore
    └── api/
```

---

## Compose Requirements

### `ui` service

- build context from `uis/`
- run both Next apps concurrently
- expose ports `3000` and `3001`
- mount:
  - `./uis:/app/uis`
  - `./src:/app/src` (shared root source imports for backoffice)
  - node_modules named volumes for each app
- use root `.env` + docker-specific proxy targets

### `backend` service

- build from root with `services/Dockerfile`
- expose port `8000`
- mount:
  - `./services/api:/app`
  - `./packages:/app/packages`
- run uvicorn with `--reload`

### Network policy

- one explicit shared network (example `brasaland-dev-net`)
- UI talks to backend via `http://backend:8000`

---

## Inter-service URL Policy

Inside containers:

- `http://backend:8000` ✅
- `http://localhost:8000` ❌

From host browser:

- website: `http://localhost:3000`
- backoffice: `http://localhost:3001`
- api/docs: `http://localhost:8000/docs`

---

## Security and Version Control

- root `.env` remains gitignored
- rotate any accidentally exposed key
- never commit real credentials in:
  - compose files
  - Dockerfiles
  - startup scripts

---

## Acceptance Criteria

- `docker compose up --build` starts all services on expected ports
- website and backoffice both reload on code changes
- backend reload works on Python changes
- backoffice API proxy resolves via service name (`backend`)
- no runtime dependency on host-only paths
- no committed real secrets in infra artifacts

---

## Verification Checklist

1. Root `.env` exists with required keys.
2. Compose build succeeds.
3. Website responds on `3000`.
4. Backoffice responds on `3001`.
5. API responds on `8000`.
6. Backoffice auth/API calls succeed.
7. Live reload works after editing UI/API source.
8. `git status` shows `.env` is untracked.

---

_Supersedes prior numbering where this document appeared as context-13._
