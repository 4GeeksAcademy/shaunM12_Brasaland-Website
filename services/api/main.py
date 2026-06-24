from __future__ import annotations

import io
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from auth.dependencies import get_current_user
from auth.routes import router as auth_router
from database import get_suppliers_table
from incident_analyzer import analyze_from_bytes, build_results_rows
from incident_analyzer.store import get_result, save_result
from suppliers.routes import router as suppliers_router
from suppliers.repository import seed_suppliers
from users.routes import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not get_suppliers_table().all():
        seed_suppliers()
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

# Auth/users mount at bare prefixes (per the AUTH-01 spec); suppliers stays under
# /api to match the existing Next.js proxy. Each route is mounted exactly once.
app.include_router(auth_router, prefix="/auth")
app.include_router(users_router, prefix="/users")
app.include_router(suppliers_router, prefix="/api/suppliers", dependencies=_protected)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/incidents/analyze", dependencies=_protected)
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


@app.get("/api/incidents/results/export", dependencies=_protected)
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
