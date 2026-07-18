# Brasaland Backoffice

App interna Next.js + TypeScript (incidentes, proveedores, inventario, reporting, …).

> Visión general: [../../README.es.md](../../README.es.md) · API: [../../services/api/README.md](../../services/api/README.md) · Inglés: [README.md](./README.md)

## Rutas principales

| Ruta | Propósito |
| ---- | --------- |
| `/` | Pipeline de talento (tracker 4Geeks) |
| `/candidates/[id]` | Detalle de candidato |
| `/data-processing` | Dashboard Milestone 2 (`src/`) |
| `/incidents` | Gestor de incidentes + analizador CSV |
| `/suppliers` | Directorio de proveedores |
| `/inventory` | Inventario de ingredientes |
| `/reporting` | KPIs semanales por ubicación (`POST /reporting/pipeline-runs` devuelve `task_id`; necesita Redis + worker Celery — ver README de la API) |

Las páginas que llaman a la API necesitan FastAPI en el puerto 8000. Para **Run pipeline** en `/reporting`, arranca también Redis y el worker Celery ([services/api/README.md](../../services/api/README.md#celery-worker-dev-55)).

## Desarrollo

```bash
# Terminal 1 — API
npm run api:install && npm run api:dev

# Terminal 2 — Redis + worker Celery (para encolar el pipeline de reporting)
docker compose up -d redis
cd services/api && uv run celery -A celery_app worker --loglevel=info

# Terminal 3 — backoffice
cp ../../.env.example ../../.env
cd uis/backoffice && npm install && npm run dev
```

Variables desde el `.env` de la **raíz** del repo. Ver [README.md](./README.md) en inglés para la lista completa.

## Build

```bash
npm run build && npm run start
```
