# Brasaland API

FastAPI service for Brasaland backoffice tools: incident CSV analysis and the procurement supplier directory.

## Package layout

- `incident_analyzer/` — milestone 5 incident CSV analysis
- `suppliers/` — Milestone 09 supplier directory (Pydantic models, TinyDB repository, routes)
- `database.py` — TinyDB initialisation
- `seed.py` — initial supplier seed loader

## Setup

Using **uv** (recommended for seeding):

```bash
cd services/api
uv sync
uv run seed
```

Or from the repo root:

```bash
npm run api:sync
npm run api:seed
```

Using **pip** (legacy):

```bash
pip install -r services/api/requirements.txt
```

## Run

```bash
npm run api:dev
```

Seed suppliers manually (skips duplicates):

```bash
cd services/api && uv run seed
```

Or:

```bash
npm run api:seed
```

On first API startup, suppliers are auto-seeded when the database is empty.

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
cd services/api && python -m pytest tests/ -q
```
