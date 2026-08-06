# Brasaland Context Index

Ordered index of historical reference context documents.

## Context Files

- `context-1-milestone-1.md` — **Canonical Milestone 1 spec** (public website + Brasa Points form; root `CONTEXT.md` is repo-wide company context only)
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
- `context-23-support-agent-langgraph-p1.md` — Support agent LangGraph Part 1 (implemented): RAG split, LangGraph + SQLite checkpoint, `POST /agent/query`, `/support` backoffice UI
- `context-23-support-agent-langgraph-p2.md` — Support agent LangGraph Part 2 (implemented): rule-based classifier, incident/inventory HTTP tools, auth forwarding, fallbacks, routing evals
- `context-24-mcp-company-tools.md` — MCP server (OAuth/mcpauth) for incidents + read-only inventory; agent incidents migration via langchain-mcp-adapters; ops UX stretch (P24-OPT); **implemented P24-4**
- `context-25-securing-agents-harness-guardrails.md` — SEC-114 Support Agent harness + guardrails (prompt hardening, input/content/security layers, sanitization, output validation, observability, CI tests; manual evaluation rubric)
- `context-26-milestone-8-agent-memory.md` — MEM-092 agent memory + self-improvement (P26-0–P26-6 complete; Postgres store, propose/confirm/audit, graph integration; evidence in `docs/agent/memory-evidence.md`)
- `context-27-milestone-9-rfp-intake-routing-p1.md` — **Milestone 9 Part 1 (parent spec):** shared §1–§9 + RFP intake/routing — `/rfp` API + UI, LangGraph, MarkItDown, classifier, OWS, Postgres, locked decisions M9-1–H8
- `context-27-milestone-9-rfp-response-generation-p2.md` — **Milestone 9 Part 2:** response generation + evaluation — generators, evaluators, loop, `POST .../draft` (**27 decisions confirmed 2026-08-06** — read p1 §1–§9 first)
- `context-27-milestone-9-rfp-approval-document-p3.md` — **Milestone 9 Part 3:** HITL approval + final document — interrupt/resume, arbitration, CEO gate, E2E (**14 decisions locked 2026-08-06** — read p1 §1–§9 + p2 first)
- Seed PDFs (when added): `assets/milestone-9/CONTEXT-brasaland-request-{1,2,3}.pdf` under `memory-bank/historical-reference/`

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
- `context-23` is reserved for the support agent LangGraph workstream: Part 1 (graph migration + `/agent` + `/support` UI) and Part 2 (live service tools + auto-routing) as companion files `-p1` / `-p2`.
- `context-24` is reserved for the MCP company-tools workstream (FastMCP + mcpauth + agent incidents migration + ops UX stretch).
- `context-25` is reserved for SEC-114 agent harness and guardrails (Support Agent `/agent/query`).
- `context-26` is reserved for MEM-092 agent memory and self-improvement (Support Agent `/agent/query`, Milestone 8).
- `context-27` is reserved for Milestone 9 agentic RFP workflow: Part 1 parent spec (`-p1`) plus companion `-p2` / `-p3` for generation/evaluation and HITL approval. **Not** `context-9` (error-handling).
- `context-9` currently has three related companion files by design.
