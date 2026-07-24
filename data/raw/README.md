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
- Read `docs/forecasting/CONTEXT-brasaland.md` before training (column meanings, date range, seasonality).
- The full 10-year file belongs in this folder. The **8-year train / 2-year test** split happens in code (`data/forecasting/`), not by splitting the CSV.
- Python ML stack lives in `services/api/` — run `cd services/api && uv sync` before the notebook or tests.

## Git

`brasaland_sales.csv` is allowed to be tracked (see root `.gitignore`). Nightly telemetry exports (`telemetry_YYYY-MM-DD.csv`) remain ignored.
