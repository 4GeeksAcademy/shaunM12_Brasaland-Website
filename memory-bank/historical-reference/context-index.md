# Brasaland Context Index

Ordered index of historical reference context documents.

## Context Files

- `context-1-milestone-1.md` — Milestone 1
- `context-2-milestone-2.md` — Milestone 2
- `context-3-milestone-3.md` — Milestone 3
- `context-4-milestone-4.md` — Milestone 4
- `context-5-incident-file-analyzer.md` — Incident file analyzer
- `context-6-supplier-directory.md` — Supplier directory
- `context-7-authentication-and-route-restriction.md` — Auth + route restriction
- `context-8-authentication-flows-frontend.md` — Frontend authentication flows
- `context-9-error-handling.md` — Error handling
- `context-9-error-handling-audit.md` — Error handling audit notes
- `context-9-error-handling-execution-roadmap.md` — Error handling roadmap
- `context-10-unit-testing.md` — Unit testing
- `context-11-milestone-5-backend-inventory-management.md` — Backend inventory
- `context-12-milestone-5-backoffice-inventory-interface.md` — Backoffice inventory UI
- `context-13-centralized-incident-manager.md` — Centralized incident manager
- `context-13-centralized-incident-manager-execution-roadmap.md` — Incident manager roadmap
- `context-14-containerization.md` — Repository containerization
- `context-15-telemetry-plan.md` — Telemetry Phase 1 design (inventory KPIs + event schemas; course floor aligned)
- `context-15-course-alignment-plan.md` — Locked decisions remapping Wave 1 telemetry to course floor
- `context-15-telemetry-frontend-capture.md` — Frontend capture phase
- `context-15-backend-storage.md` — Backend storage phase
- `context-15-telemetry-report.md` — Telemetry report phase
- `context-16-milestone-6-data-pipeline-design.md` — Milestone 6 Phase 1 data pipeline design
- `context-16-milestone-6-resilient-data-pipeline.md` — Milestone 6 Phase 2 resilient Prefect pipeline + reporting APIs
- `context-16-milestone-6-pipeline-subflows-tests.md` — Milestone 6 Phase 3 subflows, tests, `/reporting` dashboard
- Shared design: `docs/pipelines/PIPELINE_DESIGN.md` (pointer: `data/pipelines/PIPELINE_DESIGN.md`)
- `context-17-background-processes-nightly-telemetry.md` — DEV-53 nightly telemetry export + pipeline trigger (`job_runs`)
- `context-18-message-queues-async-tasks.md` — DEV-55 Redis + Celery async tasks (`POST /reporting/pipeline-runs`, `GET /tasks/{task_id}`, DLQ)
- `context-19-sales-forecasting-regression.md` — Sales forecasting with Random Forest, Brasaland course CONTEXT, 8yr/2yr split, holdout metrics (MSE, MAPE, PSI, Gini, K2), V1–V8 visuals
- `context-20-evaluating-regression-model.md` — Evaluate context-19 RF (learning curve, walk-forward CV, structural PSI, EVALUATION-report, V9–V10); read-only on context-19 code
- `context-21-rag-knowledge-base.md` — Milestone 7 RAG & knowledge base (Qdrant, setup/embed/retrieve/query, `/knowledge` API + backoffice UI, locked L1–L13)
- `context-22-route-conventions.md` — **Current** FastAPI mounts, backoffice `/api/*` proxy, auth rewrites, query-param casing (supersedes legacy path notes)

## Numbering Notes

- `context-13` is reserved for the centralized incident manager workstream.
- `context-14` is reserved for containerization.
- `context-15` is reserved for telemetry (plan, alignment, capture, storage, report companions).
- `context-16` is reserved for Milestone 6 data pipeline: Phase 1 design, Phase 2 resilient pipeline, Phase 3 subflows/tests/dashboard.
- `context-17` is reserved for background processes / nightly telemetry script (DEV-53).
- `context-18` is reserved for message queues / async tasks with Redis and Celery (DEV-55).
- `context-19` is reserved for sales forecasting / regression model (Finance prediction ticket; Brasaland course CONTEXT + repo implementation locks).
- `context-20` is reserved for evaluating the context-19 regression model (diagnostics + technical report; does not retrain or change holdout metrics).
- `context-21` is reserved for Milestone 7 RAG & knowledge base (Qdrant + FastAPI `/knowledge` + backoffice UI; decisions L1–L13 locked 2026-07-28).
- `context-22` is reserved for route/proxy conventions superseding legacy path wording in contexts 7, 8, 13, and 21 (locked 2026-07-28).
- `context-9` currently has three related companion files by design.
