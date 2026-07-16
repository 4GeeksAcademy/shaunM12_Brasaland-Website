# `scripts` folder

Helper scripts for the monorepo: CLIs, data generation, and background orchestration that do not belong inside a single app package.

> Spanish: [README.es.md](./README.es.md) · Parent: [../README.md](../README.md)

---

## Catalog

| Script | Purpose |
| ------ | ------- |
| `nightly_export.py` | DEV-53: export UTC-day telemetry CSV + trigger Milestone 6 pipeline; writes `reporting.job_runs` |
| `nightly_scheduler.py` | Separate process: wait until 02:00 America/Bogota, then run `nightly_export.py` |
| `crontab.nightly` | Equivalent crontab for host/supercronic |
| `analyze.py` | Incident CSV analyzer (Phase 1 CLI) |
| `build_incidents_csv.py` | Regenerate `data/incidents-brasaland.csv` |
| `serve-*.cjs`, `brasaland-cli.cjs`, `functions-cli.cjs` | Root Node helpers (see root `package.json`) |

---

## Nightly telemetry (DEV-53)

Independent of FastAPI. Exports `data/raw/telemetry_YYYY-MM-DD.csv` (backup only; pipeline reads the DB), then runs the Milestone 6 pipeline subprocess.

```bash
npm run api:nightly-export
TARGET_DATE=2026-07-14 npm run api:nightly-export
```

Or: `cd services/api && uv run python ../../scripts/nightly_export.py`

**Schedule:** `0 2 * * *` with `TZ=America/Bogota`  
**Docker:** `nightly-worker` in `docker-compose.yml` runs `nightly_scheduler.py`  
Status helpers: `services/api/job_runner/`

---

## Incident analyzer (`analyze.py`)

```bash
pip install -r scripts/requirements.txt
python scripts/analyze.py data/incidents-brasaland.csv
```

Validates context-5 rules, prints a summary, optionally writes `results.csv`.  
Dataset: `data/incidents-brasaland.csv` (regenerate via `build_incidents_csv.py`).

API equivalent lives in `services/api/incident_analyzer/` — see [services/api/README.md](../services/api/README.md) (`POST /api/incidents/analyze`).
