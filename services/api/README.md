# Incident Analyzer API

FastAPI service exposing incident CSV analysis endpoints used by the backoffice UI and shared with `scripts/analyze.py`.

## Setup

```bash
pip install -r services/api/requirements.txt
```

## Run

```bash
uvicorn main:app --app-dir services/api --reload --port 8000
```

## Endpoints

- `POST /api/incidents/analyze` — multipart CSV upload, returns JSON summary
- `GET /api/incidents/results/export` — downloads the last analysis as `results.csv`
- `GET /api/health` — health check
