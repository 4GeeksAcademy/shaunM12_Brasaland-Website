from __future__ import annotations

import io

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from incident_analyzer.core import analyze_from_bytes, build_results_rows
from incident_analyzer.store import get_result, save_result

app = FastAPI(title="Brasaland Incident Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/incidents/analyze")
async def analyze_incidents(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Incorrect format: upload must be a .csv file",
        )

    payload = await file.read()
    if not payload.strip():
        raise HTTPException(status_code=400, detail="Empty file: CSV has no content")

    try:
        result = analyze_from_bytes(payload, source_path=file.filename)
    except ValueError as exc:
        message = str(exc)
        if "empty" in message.lower():
            raise HTTPException(status_code=400, detail=f"Empty file: {message}") from exc
        raise HTTPException(status_code=400, detail=f"Incorrect format: {message}") from exc

    save_result(result)
    return result


@app.get("/api/incidents/results/export")
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
