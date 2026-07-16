# Brasaland Website — Monorepo de Ingeniería de IA

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)

Proyecto transversal Brasaland del programa **Ingeniería de IA — 4Geeks Academy**: backend FastAPI, sitio y backoffice Next.js, utilidades TypeScript compartidas, pipelines de datos y tooling de agentes.

> Instrucciones en inglés: [README.md](./README.md)

---

## Propósito

Construir entregables del escenario Brasaland a lo largo de los hitos del curso (Web, Programación, Backend, Telemetría, RAG, Agentes, Workflows, Tiempo real).

Contexto de negocio: [CONTEXT.md](./CONTEXT.md)  
Notas históricas por hito: [memory-bank/historical-reference/context-index.md](./memory-bank/historical-reference/context-index.md)

---

## Mapa del repositorio

```text
├── services/api/     Backend FastAPI (auth, inventario, incidentes, telemetría, reporting)
├── uis/              Apps Next.js (website + backoffice)
├── src/              Utilidades TypeScript compartidas (Milestone 2)
├── scripts/          CLIs, export nocturno, helpers de datos
├── data/             Datasets, transforms del pipeline, artefactos raw/eval
├── docs/             Arquitectura y diseños
├── agents/           Patrones y tools de agentes
├── skills/           Skills reutilizables
├── packages/shared/  Validación Python compartida
└── memory-bank/      Notas de trabajo y contextos históricos
```

El detalle vive junto a cada área — usa el mapa de documentación de abajo.

---

## Inicio rápido

```bash
npm install
cp .env.example .env   # define JWT_SECRET_KEY y demás secretos

npm run api:install
npm run api:dev

# Backoffice (otra terminal)
cd uis/backoffice && npm install && npm run dev
```

Sitio público: `cd uis/website && npm install && npm run dev`  
Docker Compose: ver `docker-compose.yml` (`backend`, `ui`, `nightly-worker`).

---

## Mapa de documentación

| Área | README | Contenido |
| ---- | ------ | --------- |
| API | [services/api/README.md](./services/api/README.md) | Setup, env, auth, seeds, endpoints, tests |
| UIs (índice) | [uis/README.md](./uis/README.md) | Apps de esta carpeta |
| Sitio público | [uis/website/README.md](./uis/website/README.md) | Sitio corporativo Next.js |
| Backoffice | [uis/backoffice/README.md](./uis/backoffice/README.md) | UI de operaciones, proxies, env |
| Scripts | [scripts/README.md](./scripts/README.md) | Analizador, export/scheduler nocturno |
| Docs | [docs/README.md](./docs/README.md) | Enlaces a diseño de pipeline y telemetría |
| Agentes | [agents/README.md](./agents/README.md) | Catálogo de plantillas |
| Skills | [skills/README.md](./skills/README.md) | Catálogo de skills |

TypeScript compartido (`src/`): `npm run typecheck`, `npm test`, `npm run demo`.  
Servidores auxiliares en raíz: `npm run serve` / `serve:src` / `serve:stop` (ver `package.json`).

---

## Hitos (referencia)

| Hito | Enfoque | Entregables típicos |
| ---- | ------- | ------------------- |
| 0 | Prework | Entorno |
| 1 | Web | Sitio corporativo |
| 2 | Programación | Lógica en `src/` |
| 3–4 | UI / Next.js | Apps en `uis/` |
| 5 | Backend | API en `services/api/` |
| 6 | Telemetría / pipeline | Telemetría, reporting, Prefect |
| 7–10 | RAG, agentes, workflows, tiempo real | Agentes, skills, automatización |

---

## Enlaces

- [4Geeks Academy — Ingeniería de IA](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [Cómo empezar un proyecto de código](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contribuidores

Plantilla del programa de Ingeniería de IA de 4Geeks Academy ([@marcogonzalo](https://www.linkedin.com/in/marcogonzalo), [@alezanchezr](https://x.com/alesanchezr) y colaboradores).  
[Curso de Ingeniería de IA](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia) · [GitHub](https://github.com/4geeksacademy)
