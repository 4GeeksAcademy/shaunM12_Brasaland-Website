# Brasaland Backoffice

App interna Next.js + TypeScript (incidentes, proveedores, inventario, reporting, …).

> Visión general: [../../README.es.md](../../README.es.md) · API: [../../services/api/README.md](../../services/api/README.md) · Convenciones de rutas: [context-22](../../memory-bank/historical-reference/context-22-route-conventions.md) · Inglés: [README.md](./README.md)

## Rutas principales

| Ruta | Propósito |
| ---- | --------- |
| `/` | Pipeline de talento (tracker 4Geeks) |
| `/candidates/[id]` | Detalle de candidato |
| `/data-processing` | Dashboard Milestone 2 (`src/`) |
| `/registration-analytics` | Analítica de registros Brasa Points |
| `/incidents`, `/incidents/[id]` | Gestor de incidentes + detalle |
| `/suppliers`, `/suppliers/[id]` | Directorio y detalle de proveedores |
| `/inventory` | Redirige a `/inventory/products` |
| `/inventory/products`, `/inventory/orders/*` | Stock, entradas/salidas e historial |
| `/reporting` | KPIs semanales (`task_id` vía Celery — ver README API) |
| `/knowledge` | Consulta RAG + reindex (requiere Qdrant) |
| `/account/profile`, `/account/users` | Perfil y usuarios (admin) |
| `/login`, `/register`, `/forgot-password`, … | Auth público |

Las páginas que llaman a la API necesitan FastAPI en **`http://127.0.0.1:8000`**. Sitio público aparte: `uis/website` (puerto 3001 habitual).

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

### Proxy API

El backoffice reescribe `/api/<dominio>/*` hacia FastAPI (`/incidents`, `/suppliers`, `/inventory`, `/reporting`, `/knowledge`, `/telemetry`, `/tasks`). Auth: `/auth/*`, `/users/*`. Variable: `BACKOFFICE_API_PROXY_TARGET`. Overrides opcionales: `NEXT_PUBLIC_*_API_BASE_URL` (incl. `NEXT_PUBLIC_KNOWLEDGE_API_BASE_URL`).

### Parámetros de consulta

- **URLs del navegador:** camelCase (`?productId=7&locationId=3`).
- **Llamadas FastAPI:** snake_case (`?location_id=3`, `?week_start=2026-07-21`).
- Helpers en `lib/query-params.ts`; mapeo en los clientes API de `lib/`.

## Build

```bash
npm run build && npm run start
```
