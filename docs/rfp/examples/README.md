# RFP workflow examples (Milestone 9)

Tracked sample outputs for PR review and documentation. Runtime uploads and mirrors under `data/raw/intakes/{ticket_id}/` remain gitignored.

## Sunset Bay — CEO path (seed #1)

| | Path |
|---|------|
| **Input RFP** | [`memory-bank/historical-reference/assets/milestone-9/CONTEXT-brasaland-request-1.pdf`](../../../memory-bank/historical-reference/assets/milestone-9/CONTEXT-brasaland-request-1.pdf) |
| **Final proposal** | [`sunset-bay/final_proposal.md`](./sunset-bay/final_proposal.md) |
| **Flow** | 4 departments (incl. training) → CEO gate → `completed` |

## Andes Tech — no CEO (seed #2)

| | Path |
|---|------|
| **Input RFP** | [`memory-bank/historical-reference/assets/milestone-9/CONTEXT-brasaland-request-2.pdf`](../../../memory-bank/historical-reference/assets/milestone-9/CONTEXT-brasaland-request-2.pdf) |
| **Final proposal** | [`andes-tech/final_proposal.md`](./andes-tech/final_proposal.md) |
| **Flow** | 3 departments → `completed` (no CEO) |

## Reproduce (simulated department + CEO approvals)

```bash
# CEO path (matches sunset-bay example shape)
cd services/api && uv run python ../../scripts/rfp_e2e_smoke.py --seed 1

# No CEO (matches andes-tech example shape)
cd services/api && uv run python ../../scripts/rfp_e2e_smoke.py --seed 2
```

Integration tests (same simulated approvals, mocked LLM for CI):

```bash
cd services/api && uv run python -m pytest tests/pipelines/test_rfp_e2e.py -q
```

- `test_e2e_seed1_ceo_path_completed` — seed #1
- `test_e2e_seed2_intake_draft_approval_completed` — seed #2

These examples were captured from completed UI runs; smoke/E2E produce equivalent deterministic output for reviewers without the backoffice.
