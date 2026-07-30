from __future__ import annotations

import io
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from auth.dependencies import get_current_user
from auth.routes import router as auth_router
import config
from database import get_engine, get_suppliers_table
from incident_analyzer import analyze_from_bytes, build_results_rows
from incident_analyzer.store import get_result, save_result
from incidents.routes import router as incidents_router
from inventory.routes import router as inventory_router
from seeds.inventory import ensure_inventory_schema, seed_inventory_if_empty
from suppliers.routes import router as suppliers_router
from suppliers.repository import seed_suppliers
from telemetry.routes import router as telemetry_router
from telemetry.models import ensure_telemetry_schema
from reporting.routes import router as reporting_router
from reporting.models import ensure_reporting_schema
from job_runner.models import ensure_job_runs_schema
from task_dead_letters.models import ensure_task_dead_letters_schema
from users.routes import router as users_router
from tasks.routes import router as tasks_router
from knowledge.routes import router as knowledge_router
from sqlmodel import SQLModel
from sqlmodel import Session

import inventory.models  # noqa: F401 — register ORM tables with SQLModel metadata
import incidents.models  # noqa: F401 — register ORM tables with SQLModel metadata
import telemetry.models  # noqa: F401 — register telemetry ORM tables
import reporting.models  # noqa: F401 — register reporting ORM tables
import job_runner.models  # noqa: F401 — register job_runs ORM table
import task_dead_letters.models  # noqa: F401 — register task_dead_letters ORM table


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not get_suppliers_table().all():
        seed_suppliers()
    if config.DATABASE_URL:
        with Session(get_engine()) as session:
            ensure_reporting_schema(session)
            ensure_job_runs_schema(session)
            ensure_task_dead_letters_schema(session)
        SQLModel.metadata.create_all(get_engine())
        with Session(get_engine()) as session:
            ensure_telemetry_schema(session)
            ensure_inventory_schema(session)
            ensure_reporting_schema(session)
            ensure_job_runs_schema(session)
            ensure_task_dead_letters_schema(session)
        seed_inventory_if_empty()
    yield


app = FastAPI(
    title="Brasaland API",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_protected = [Depends(get_current_user)]

# Domain routers use bare FastAPI prefixes. The backoffice exposes browser-facing
# `/api/*` paths through Next.js rewrites so UI and API routes never collide.
app.include_router(auth_router, prefix="/auth")
app.include_router(users_router, prefix="/users")
app.include_router(suppliers_router, prefix="/suppliers", dependencies=_protected)
app.include_router(inventory_router, prefix="/inventory")
app.include_router(incidents_router, prefix="/incidents", dependencies=_protected)
app.include_router(telemetry_router, prefix="/telemetry")
app.include_router(reporting_router, prefix="/reporting", dependencies=_protected)
app.include_router(tasks_router, prefix="/tasks", dependencies=_protected)
app.include_router(knowledge_router, prefix="/knowledge", dependencies=_protected)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/incidents/analyze", dependencies=_protected)
async def analyze_incidents(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Incorrect format: upload must be a .csv file",
        )

    payload = await file.read()
    if not payload.strip():
        raise HTTPException(
            status_code=400, detail="Empty file: the CSV has no content."
        )

    try:
        result = analyze_from_bytes(payload, source_path=file.filename)
    except ValueError as exc:
        # `analyze_from_bytes` raises only curated, user-safe messages (the raw
        # parser error is logged inside the analyzer, never surfaced here).
        if "empty" in str(exc).lower():
            raise HTTPException(
                status_code=400, detail="Empty file: the CSV has no content."
            ) from exc
        raise HTTPException(
            status_code=400,
            detail="Incorrect format: the file could not be read as a valid CSV.",
        ) from exc

    save_result(result)
    return result


@app.get("/incidents/results/export", dependencies=_protected)
def export_results() -> StreamingResponse:
    result = get_result()
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No analysis available. Upload a CSV file first.",
        )

    rows = build_results_rows(result)
    csv_buffer = io.StringIO()
    pd.DataFrame(rows).to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="results.csv"'},
    )
