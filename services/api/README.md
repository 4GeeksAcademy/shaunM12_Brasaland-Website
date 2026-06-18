# Brasaland API

FastAPI service for Brasaland backoffice tools: incident CSV analysis and the procurement supplier directory.

## Package layout

- `incident_analyzer/` — milestone 5 incident CSV analysis
- `suppliers/` — Milestone 09 supplier directory (Pydantic models, TinyDB repository, routes)
- `database.py` — TinyDB initialisation
- `seed.py` — initial supplier seed loader

This service uses **[uv](https://docs.astral.sh/uv/)**. The virtual environment lives in `services/api/.venv` and is created/managed by `uv` from `pyproject.toml`. Never commit `.venv`.

## Setup

Install dependencies (creates `services/api/.venv`):

```bash
cd services/api
uv sync
```

Or from the repo root:

```bash
npm run api:install   # alias for: cd services/api && uv sync
```

## Run

From the repo root:

```bash
npm run api:dev       # http://127.0.0.1:8000
```

Or directly:

```bash
cd services/api
uv run uvicorn main:app --reload --port 8000
```

## Seed

On first API startup, suppliers are auto-seeded when the database is empty. To seed manually (skips duplicates):

```bash
npm run api:seed      # or: cd services/api && uv run seed
```

## Incident endpoints

- `POST /api/incidents/analyze` — multipart CSV upload, returns JSON summary
- `GET /api/incidents/results/export` — downloads the last analysis as `results.csv`
- `GET /api/health` — health check

## Supplier endpoints

Mounted at both `/api/suppliers` and `/suppliers`:

- `POST /api/suppliers` — register supplier (422 on invalid input)
- `GET /api/suppliers?country=&category=` — list with optional filters
- `GET /api/suppliers/{id}` — supplier detail (404 if missing)
- `PATCH /api/suppliers/{id}/rate` — update rate and `rate_updated_at`
- `PATCH /api/suppliers/{id}/status` — activate or suspend
- `PATCH /api/suppliers/{id}/notes` — update procurement notes
- `DELETE /api/suppliers/{id}` — remove erroneous record (404 if missing)

## Tests

```bash
npm run api:test      # or: cd services/api && uv run pytest tests/ -q
```
