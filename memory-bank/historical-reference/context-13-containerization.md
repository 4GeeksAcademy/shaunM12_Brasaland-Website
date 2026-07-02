# CONTEXT — Repository Containerization for Development · Brasaland

## AI Engineering - 4Geeks Academy

> **Ticket:** INFRA-40 — Dockerize full monorepo development stack
> **Repository index:** `context-13-containerization.md`
> **Type:** Infrastructure / developer experience
> **Status:** 🟡 Planned (not yet implemented)

### Locked decisions

- **Single UI container:** both `uis/website` and `uis/backoffice` run inside one container.
- **Hot reload required:** both UI apps and FastAPI backend run in development mode with reload.
- **Compose as entrypoint:** from repo root, one `docker compose up` must boot the full platform.
- **Service-name networking:** inter-service URLs must use Docker service names (never `localhost` between containers).
- **Environment-driven config:** no hardcoded service URLs, secrets, or API keys in Dockerfiles or `docker-compose.yml`.
- **Root `.env` first:** create root `.env` before writing `docker-compose.yml`.
- **Security baseline:** `.env` must be gitignored; versioned files must never include real credentials.

---

## Focus

Brasaland needs deterministic local environments: any engineer should clone the repository, run one command, and start productive development without host dependency drift or setup troubleshooting.

This work containerizes:

- `uis/website` (public-facing Next.js app),
- `uis/backoffice` (internal admin Next.js app),
- `services/api` (FastAPI backend with reload),

all orchestrated via Docker Compose from the repository root.

---

## Scope

### In scope

- Dockerfile for UI in `uis/` that starts **both** Next.js apps.
- Dockerfile for backend in `services/` that starts FastAPI with reload.
- `.dockerignore` for both `uis/` and `services/`.
- Root `docker-compose.yml` with:
  - `ui` service (single container for both frontends),
  - `backend` service,
  - explicit named network,
  - bind mounts for live code reload,
  - environment variables loaded from root `.env`.
- Root `.env` creation and wiring.
- Verify `.env` is excluded via `.gitignore`.

### Out of scope

- Production-grade image hardening and deployment manifests.
- Secret management beyond local `.env` for development.
- CI/CD rollout automation.

---

## Required file layout

```text
/
├── .env                         # local dev config (gitignored)
├── docker-compose.yml
├── .gitignore
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

## Implementation requirements

### 1) Root `.env` (must exist before compose)

Create root `.env` first. It must contain all service variables used by compose and app runtime.

Minimum variables (example keys):

- `WEBSITE_PORT=3000`
- `BACKOFFICE_PORT=3001`
- `API_PORT=8000`
- `BACKOFFICE_API_PROXY_TARGET=http://backend:8000`
- `INCIDENTS_API_PROXY_TARGET=http://backend:8000`
- backend runtime values required by `services/api` (JWT, database URL, etc.) as needed for local dev

Use placeholders or dev-only values. Never commit real secrets.

### 2) UI Dockerfile (`uis/Dockerfile`)

- Base image: official Node Alpine image.
- Install dependencies for:
  - `uis/website`
  - `uis/backoffice`
- Set working directory under `/app/uis` (or equivalent).
- Copy and make executable `start.sh`.
- Default `CMD` runs `start.sh`.

`start.sh` responsibilities:

- start `website` dev server on `3000`,
- start `backoffice` dev server on `3001`,
- run both concurrently and keep container alive,
- preserve stdout/stderr logs for both processes.

### 3) UI `.dockerignore` (`uis/.dockerignore`)

Must include at minimum:

- `node_modules`
- `.next`
- `.env*`
- `*.log`

### 4) Backend Dockerfile (`services/Dockerfile`)

- Base image: official Python image.
- Install backend dependencies from `requirements.txt`.
- Start FastAPI with reload enabled (`uvicorn ... --reload`).

If the repo currently uses `uv`/`pyproject.toml`, either:

- generate and commit a `requirements.txt` for container use, or
- align this requirement with the tech lead explicitly.

### 5) Backend `.dockerignore` (`services/.dockerignore`)

Must include at minimum:

- `__pycache__`
- `*.pyc`
- `.env*`
- `tests/`
- `*.log`

### 6) Docker Compose (`/docker-compose.yml`)

Define two services:

- `ui`
  - build from `/uis`
  - bind mount source for hot reload
  - expose host ports:
    - `3000` website
    - `3001` backoffice
  - load env from root `.env`
- `backend`
  - build from `/services`
  - bind mount source for reload
  - expose host port `8000`
  - load env from root `.env`

Networking:

- define one explicit named network (for example `brasaland-dev-net`),
- attach both services to it,
- inter-service calls must use `backend` as host (or whichever backend service name is defined), never `localhost`.

---

## Inter-service URL policy (critical)

Inside containers:

- ✅ `http://backend:8000`
- ❌ `http://localhost:8000` (for container-to-container traffic)

From host browser:

- `http://localhost:3000` (website)
- `http://localhost:3001` (backoffice)
- `http://localhost:8000` (API/docs/health)

---

## Security and version-control requirements

- Never place real secrets in:
  - `docker-compose.yml`
  - Dockerfiles
  - shell scripts
- Root `.env` must be in `.gitignore`.
- If a secret is committed by mistake:
  - treat it as compromised,
  - rotate it immediately,
  - remove from history if policy requires.

---

## Acceptance criteria

- `docker compose up` from repo root starts:
  - website on `3000`,
  - backoffice on `3001`,
  - API on `8000`.
- UI hot reload works for both frontends.
- Backend reload works on Python code changes.
- Backoffice-to-API connectivity works via Docker service name (not localhost).
- Compose env values come from root `.env`, not hardcoded inline.
- `.env` is gitignored.
- No real credentials exist in tracked Docker artifacts.

---

## Verification checklist

1. Root `.env` exists and contains required keys.
2. `docker compose build` passes.
3. `docker compose up` boots all services.
4. Website and backoffice open on expected ports.
5. API health endpoint responds.
6. Backoffice API requests resolve to `backend` service host.
7. File edits in:
   - `uis/website`,
   - `uis/backoffice`,
   - `services/api`,
   trigger live reload.
8. `git status` confirms `.env` is not tracked.
9. Compose and Dockerfiles contain no real secrets.

---

## Suggested PR scope

1. Root infra files (`docker-compose.yml`, `.env.example`, `.gitignore` updates).
2. UI containerization (`uis/Dockerfile`, `uis/.dockerignore`, `uis/start.sh`).
3. Backend containerization (`services/Dockerfile`, `services/.dockerignore`, requirements support).
4. Env wiring updates for service-name API URLs in both UI apps.
5. README section for containerized dev quickstart.

---

_Internal document — 4Geeks Academy · AI Engineering Track · Brasaland_
