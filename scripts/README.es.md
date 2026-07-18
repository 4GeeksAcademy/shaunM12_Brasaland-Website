# Carpeta `scripts`

Scripts auxiliares del monorepo: CLIs, generación de datos y orquestación en segundo plano que no pertenecen a un solo paquete de aplicación.

> Inglés: [README.md](./README.md) · Padre: [../README.es.md](../README.es.md)

---

## Catálogo

| Script | Propósito |
| ------ | --------- |
| `nightly_export.py` | DEV-53: export CSV de telemetría (día UTC) + dispara el pipeline Milestone 6; escribe `reporting.job_runs` |
| `nightly_scheduler.py` | Proceso aparte: espera las 02:00 America/Bogota y ejecuta `nightly_export.py` |
| `crontab.nightly` | Crontab equivalente (host/supercronic) |
| `analyze.py` | Analizador CLI de incidentes CSV (Fase 1) |
| `build_incidents_csv.py` | Regenera `data/incidents-brasaland.csv` |
| `serve-*.cjs`, `brasaland-cli.cjs`, `functions-cli.cjs` | Helpers Node de la raíz (ver `package.json`) |

---

## Telemetría nocturna (DEV-53)

Independiente de FastAPI. Exporta `data/raw/telemetry_YYYY-MM-DD.csv` (solo backup; el pipeline lee la DB) y luego lanza el subprocess del pipeline Milestone 6.

```bash
npm run api:nightly-export
TARGET_DATE=2026-07-14 npm run api:nightly-export
```

**Horario:** `0 2 * * *` con `TZ=America/Bogota`  
**Docker:** servicio `nightly-worker` en `docker-compose.yml`  
Helpers de estado: `services/api/job_runner/`

Este camino **no** es Celery. Las ejecuciones manuales on-demand del pipeline usan Redis + Celery (`celery-worker`) — ver [services/api/README.md](../services/api/README.md#celery-worker-dev-55) y [context-18](../memory-bank/historical-reference/context-18-message-queues-async-tasks.md).

---

## Analizador de incidentes (`analyze.py`)

```bash
pip install -r scripts/requirements.txt
python scripts/analyze.py data/incidents-brasaland.csv
```

Equivalente API en `services/api/incident_analyzer/` — ver [services/api/README.md](../services/api/README.md).
