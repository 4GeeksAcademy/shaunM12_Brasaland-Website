# Raw data (`data/raw/`)

## Drop your sales CSV here

**Full path:**

```text
/workspaces/shaunM12_Brasaland-Website/data/raw/brasaland_sales.csv
```

In the file explorer: **`data` → `raw` → `brasaland_sales.csv`**

A stub file is present so the name is visible. **Replace it** with the course-provided dataset (drag-and-drop → Replace).

## Rules

- Use the course-provided file only — do **not** generate or simulate sales data.
- Read [docs/forecasting/CONTEXT-brasaland.md](../docs/forecasting/CONTEXT-brasaland.md) before training (column meanings, date range, seasonality, stakeholders).
- The full 10-year file belongs in this folder. The pipeline filters **`market = consolidated`** rows only (see context-19). The **8-year train / 2-year test** split happens in code (`data/forecasting/`), not by splitting the CSV.
- Holdout evaluation reports MSE, **MAPE**, PSI, Gini, and K2 — see [docs/forecasting/README.md](../docs/forecasting/README.md).
- Python ML stack lives in `services/api/` — run `cd services/api && uv sync` before the notebook or tests.

## RFP intake uploads (`data/raw/intakes/`)

**Runtime path for UI-uploaded RFP PDFs** (Milestone 9 — context-27):

```text
data/raw/intakes/{ticket_id}/source.pdf
```

- Created by the backoffice **RFP** tab upload flow; **gitignored** (see root `.gitignore`).
- **Seed PDFs** for tests stay in `memory-bank/historical-reference/assets/milestone-9/` — do not copy them here.
- LangGraph checkpoints remain under `data/rfp/checkpoints.db` (separate from raw intake files).

## Git

`brasaland_sales.csv` is allowed to be tracked (see root `.gitignore`). Nightly telemetry exports (`telemetry_YYYY-MM-DD.csv`) remain ignored.
