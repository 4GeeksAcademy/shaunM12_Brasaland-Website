# Pipeline design (pointer)

Canonical design lives at:

**[`docs/pipelines/PIPELINE_DESIGN.md`](../../docs/pipelines/PIPELINE_DESIGN.md)**

Phase 2 entrypoint: [`pipeline.py`](./pipeline.py). Prefect lives in the **`services/api`** venv — use `uv run`, not bare `python`:

```bash
# from services/api (recommended — uses venv with prefect)
cd services/api && uv run python ../../data/pipelines/pipeline.py
```

Do **not** use `PATH=... python ...` (that is not `PYTHONPATH`) or system `python` outside the venv.

Do not treat older daily `kpi_*` quantity tables as destination for Milestone 6 Phase 1+.
