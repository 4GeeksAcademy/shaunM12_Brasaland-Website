# Brasaland Company Tools MCP Server

OAuth-protected MCP server for Brasaland **incidents manager** (read + write) and **read-only inventory** (Context 24).

Spec: [`memory-bank/historical-reference/context-24-mcp-company-tools.md`](../../memory-bank/historical-reference/context-24-mcp-company-tools.md)

## Phase status (P24-4 complete)

| Phase | Deliverable | Status |
| ----- | ----------- | ------ |
| P24-0 | `mcps/` uv scaffold, HTTP server | Done |
| P24-1 | mcpauth OAuth, protected MCP, error codes, logging | Done |
| P24-2 | `manage_incident_tickets` + `query_inventory` | Done |
| P24-3 | Agent incident **reads** via MCP; deleted `agent/tools/incidents.py` | Done |
| P24-3b | Agent incident **writes** via MCP; classifier OPT-G/F | Done |
| P24-OPT | Inventory UX, write guards, scope labels, `/support` tips | Done |
| P24-UX | Natural-language classifier + name search + UI example chips | Done |
| P24-4 | Tests, README, `.env.example`, verification checklist | Done |

## Architecture

```text
MCP Playground / external client ──OAuth──► MCP :8765/mcp
Support Agent (/agent/query) ──mint token──► MCP :8765/mcp
                                              │
                                              ▼ HTTP + Brasaland JWT
                                         FastAPI :8000
                                         /incidents  /inventory
```

- **Incidents:** all support-agent incident ops go through MCP only (no direct `/incidents` from the agent).
- **Inventory (agent):** still direct HTTP to `/inventory/products` (P24-L5). MCP `query_inventory` is for external clients.
- **`/support` incident queries** require **both** FastAPI (`:8000`) and this MCP server (`:8765`) running.

## Prerequisites

1. Create a project at [getmcpauth.dev/dashboard](https://getmcpauth.dev/dashboard)
2. Copy the **registration secret** into `MCPAUTH_REGISTRATION_SECRET` (repo root `.env`)
3. FastAPI running on `MCP_INTERNAL_API_BASE_URL` (default `http://127.0.0.1:8000`)

## Run locally

**Terminal 1 — FastAPI (repo root):**

```bash
npm run api:dev
```

**Terminal 2 — MCP server:**

```bash
cd mcps/brasaland-company-tools
uv sync
uv run brasaland-company-tools
```

Or from repo root: `npm run mcp:dev`

For **Codespaces / MCP Playground**, forward port **8765** as **Public** and set `MCP_RESOURCE_SERVER_URL` to the forwarded URL (localhost alone will not work for Playground).

Environment (see repo root `.env.example`):

```bash
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8765
MCP_RESOURCE_SERVER_URL=https://YOUR-CODESPACE-8765.app.github.dev
MCPAUTH_ISSUER_URL=https://getmcpauth.dev
MCPAUTH_REGISTRATION_SECRET=          # required
MCP_INTERNAL_API_BASE_URL=http://127.0.0.1:8000

# Support agent MCP client
AGENT_MCP_SERVER_URL=http://127.0.0.1:8765
AGENT_INTERNAL_API_BASE_URL=http://127.0.0.1:8000
AGENT_DEFAULT_LOCATION_ID=1
```

## MCP tools

### `manage_incident_tickets`

| action | Scope | Upstream |
| ------ | ----- | -------- |
| `get`, `list`, `summary` | `incidents:read` | GET `/incidents`, `/incidents/summary` |
| `create`, `update_status` | `incidents:write` | POST `/incidents`, PATCH `/incidents/{id}/status` |

List filters: `status`, `origin`, `branch`, `category`.

### `query_inventory`

| action | Scope | Upstream |
| ------ | ----- | -------- |
| `query` | `inventory:read` | GET `/inventory/products` |

Optional params: `product_id`, `sku`, `location_id` (1–14), `name` (partial match).

Write keywords or non-`query` actions → **`INVENTORY_WRITE_FORBIDDEN`**.

## Upstream auth (P24-L11)

Protected FastAPI routes require a **Brasaland JWT**, not the getmcpauth MCP token.

When testing from Inspector/Playground, add header:

```text
X-Upstream-Authorization: Bearer <brasaland-access-token>
```

The support agent passes the caller JWT automatically via the MCP client.

## Verify (P24-4 checklist)

### Automated (run locally)

```bash
# MCP unit tests (12 tests — auth, scopes, tools, write rejection)
cd mcps/brasaland-company-tools && uv run pytest tests/ -q

# Agent pipeline tests (classifier, MCP client, graph routing)
cd services/api && uv run pytest tests/pipelines/ -q \
  --ignore=tests/pipelines/test_sales_forecast_diagnose.py
```

### Manual smoke (servers running)

```bash
curl http://127.0.0.1:8765/health                    # → OK
curl http://127.0.0.1:8765/.well-known/oauth-protected-resource/mcp
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://127.0.0.1:8765/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
# → 401 without OAuth token
```

With a valid MCP token + `X-Upstream-Authorization`:

- `manage_incident_tickets` — create, list, get, summary, update_status
- `query_inventory` — read by SKU/name; write attempt returns `INVENTORY_WRITE_FORBIDDEN`

### Agent migration checks

- [x] `services/api/agent/tools/incidents.py` deleted
- [x] No direct `/incidents` HTTP from `services/api/agent/`
- [x] Incident reads/writes use `agent/mcp_client.py` → MCP
- [x] Inventory agent path unchanged (direct HTTP)
- [x] RAG vs tool routing preserved (`124` pipeline tests)

### MCP Playground (required for grading)

1. Forward Codespaces port **8765** publicly
2. Set `MCP_RESOURCE_SERVER_URL` to the forwarded URL
3. Complete OAuth in [MCP Playground](https://getmcpauth.dev) against your project
4. Call each tool once with upstream JWT header

## Known limits

Documented for support users and external integrators:

| Limit | Detail |
| ----- | ------ |
| **One topic per question** | Ask incidents **or** inventory **or** KB policy — not combined (P24-OPT-I) |
| **Inventory agent path** | Direct HTTP only; MCP inventory is for external clients |
| **No person/assignee search** | Incident model has no `reported_by` / `assigned_to` field |
| **Branch vs inventory location** | Incident branches (`miami_doral`) ≠ inventory location ids (1–14) |
| **List row caps** | Agent generation caps incident/inventory lists at 10 rows in LLM context |
| **Dual-server dependency** | `/support` incident queries need API + MCP both running |
| **Fuzzy branch aliases** | Partial names (`Doral` alone) — deferred unless added in a follow-up |

## Error codes (P24-L16)

| Code | Meaning |
| ---- | ------- |
| `AUTH_MISSING` | No bearer token (MCP or upstream) |
| `AUTH_INVALID` | Token failed mcpauth introspection |
| `AUTHZ_INSUFFICIENT_SCOPE` | Missing required scope |
| `VALIDATION_ERROR` | Invalid tool input |
| `INVENTORY_WRITE_FORBIDDEN` | Write attempt on inventory tool |
| `UPSTREAM_NOT_FOUND` | FastAPI 404 |
| `UPSTREAM_ERROR` | FastAPI 5xx / transport failure |

Reference: `GET /auth/errors`

## MCP endpoint

Streamable HTTP: `{MCP_RESOURCE_SERVER_URL}/mcp`
