# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

> _Spanish version: [README.es.md](./README.es.md)._

---

## `analyze.py` — Incident File Analyzer (Phase 1)

Analyzes Brasaland incident CSV files: validates records against context-5 rules, prints a formatted summary, and optionally exports metrics to `results.csv`.

### Requirements

```bash
pip install -r scripts/requirements.txt
```

### Usage

```bash
python scripts/analyze.py incidents-brasaland.csv
```

- **Input**: path to an incident CSV (positional argument).
- **Output**: formatted summary printed to the console.
- **Export**: at the end, answer `y` to write one-row-per-metric results to `results.csv` in the current working directory.

### Validated fields

Required columns (aliases such as `incident_id` are supported): `incident_id`, `date`, `location_id`, `category`, `description`, `status`, `reporter_id`. Optional: `customer_id`, `satisfaction_score`.

Status values are normalized to `OPEN`, `CLOSED`, or `DISCARDED` before reporting.

### Test file

- `incidents-brasaland.csv` — English context-5 dataset generated from `source-incidents-spanish.csv`
- Regenerate with: `python scripts/build_incidents_csv.py`

### API integration (Phase 2)

The analysis logic lives in `services/api/incident_analyzer/` and is also exposed via:

- `POST /api/incidents/analyze`
- `GET /api/incidents/results/export`

See [services/api/README.md](../services/api/README.md).
