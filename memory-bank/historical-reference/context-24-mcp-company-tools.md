# Context 24 — MCP Server for Company Tools · Brasaland

**Ticket:** RFP — MCP Server for company tools (incidents manager + read-only inventory)  
**Type:** New MCP server (FastMCP + mcpauth) + support agent incidents migration via langchain-mcp-adapters + ops UX hardening  
**Branch:** `mcp-connecting-agent`  
**Status:** Implemented (P24-4 complete)  
**Depends on:** [context-13-centralized-incident-manager.md](./context-13-centralized-incident-manager.md), [context-11-milestone-5-backend-inventory-management.md](./context-11-milestone-5-backend-inventory-management.md), [context-22-route-conventions.md](./context-22-route-conventions.md), [context-23-support-agent-langgraph-p2.md](./context-23-support-agent-langgraph-p2.md)  
**Stakeholders:** Tech lead (RFP author); operations / external MCP clients; support agent users

---

## Ticket brief

The support agent already queries the Incidents Manager from inside the LangGraph, but any future integration (another agent, another team, an external partner) would have to reimplement those same calls. Expose them as an independent **MCP Server**, authenticated with **OAuth**, so that any authorized MCP client can:

- **Manage** Incidents Manager tickets (create, update status, check status).
- **Query — never edit** inventory data.

The server must not grant more permissions than strictly necessary for each tool. Document discovery well: any client should understand what the server can do without additional human context.

**Migration is not optional:** replace the agent's direct Incidents Manager HTTP tool with MCP client tools via **langchain-mcp-adapters**. If the agent still calls the Incidents Manager outside the server, the ticket is not resolved.

### Design decisions resolved in this context

| Topic | Locked choice |
| ----- | ------------- |
| Transport | **Streamable HTTP** (remote clients + MCP Playground + agent client) |
| Inventory write protection | **Explicit rejection** at MCP layer — not omission |
| Discovery | Tool names, descriptions, input/output schemas sufficient for external agents |
| Agent graph topology | **Unchanged for read paths** — swap incident transport; add write path |
| Backend integration | MCP server wraps existing FastAPI services via HTTP — **does not replace** incidents/inventory modules |

---

## Prerequisite gate

- [ ] Context-13 incidents manager live (`POST/GET/PATCH /incidents`, lifecycle rules in repository)
- [ ] Context-11 inventory live (`GET /inventory/products`, stock via orders only)
- [ ] Context-23 P2 support agent merged (classifier, tool nodes, auth forwarding P2-L37)
- [ ] getmcpauth.dev project created; `MCPAUTH_REGISTRATION_SECRET` available
- [ ] FastAPI running for upstream HTTP (`AGENT_INTERNAL_API_BASE_URL` / `MCP_INTERNAL_API_BASE_URL`)

---

## Locked decisions — Core MCP (P24-L1–P24-L20)

### Foundation

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P24-L1** | Transport | **Streamable HTTP** only — stdio out of scope (Playground + remote clients require public URL) |
| **P24-L2** | Location | `mcps/brasaland-company-tools/` — own `pyproject.toml`; **not** under `services/` |
| **P24-L3** | Backend calls | HTTP to **bare FastAPI mounts** per context-22 (`/incidents`, `/inventory`) — never `/api/*` from Python; never direct repository import |
| **P24-L4** | MCP OAuth | **getmcpauth.dev** + `getmcpauth-python` (`McpAuthTokenVerifier`, `build_auth_settings`); **do not** use FastMCP built-in OAuth/auth helpers |
| **P24-L5** | Agent inventory path | **Direct HTTP unchanged** — `lookup_inventory_stock_node` → `agent/tools/inventory.py`; MCP exposes read-only `query_inventory` for external clients |
| **P24-L6** | Tool shape | **`manage_incident_tickets`** (action enum) + **`query_inventory`** (explicit write rejection) |
| **P24-L7** | Documentation | **Single context file** with embedded implementation phases |
| **P24-L8** | Dependencies | Install with **`uv add`** only — never `pip install` directly |

### Authentication

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P24-L9** | Playground / external clients | Full OAuth 2.1 flow against getmcpauth.dev project |
| **P24-L10** | Support agent token path | After validating caller JWT on `/agent/query`, API **mints** MCP token server-to-server (`mintToken` pattern); user does not re-login |
| **P24-L11** | Upstream FastAPI auth | MCP tools **forward caller's original JWT** (`Authorization: Bearer`) to incidents/inventory HTTP — same chain as P2-L37 |
| **P24-L12** | Scopes | `incidents:read`, `incidents:write`, `inventory:read` — enforce via mcpauth `required_scopes` + tool handler checks |

### Tools, agent migration, errors

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P24-L13** | Incidents actions | `create`, `update_status`, `get`, `list`, `summary` — mapped to FastAPI endpoints below |
| **P24-L14** | Field naming | Use API field **`origin`** — never `source` (P2-L5) |
| **P24-L15** | Inventory writes (MCP) | Any write signal → **`INVENTORY_WRITE_FORBIDDEN`** with explainable message |
| **P24-L16** | Error codes | Distinct codes for auth, authorization, validation, inventory-write-forbidden, upstream HTTP |
| **P24-L17** | Logging | **One log line per tool invocation:** tool name, client id/sub, action summary, result, upstream status |
| **P24-L18** | Agent envelope | MCP responses mapped to **P2-L36** envelope — `generate_support_answer` and fallbacks preserved |
| **P24-L19** | Dual path forbidden | **Delete** `services/api/agent/tools/incidents.py` — no `lookup_incidents` imports remain |
| **P24-L20** | Graph routing (read paths) | Classifier edges for `rag`, `incident`, `both`, `inventory` unchanged (P2-L23–L29) |

---

## Locked decisions — Agent incident writes (Gap 1, Option B)

| ID | Topic | Locked choice |
| -- | ----- | ------------- |
| **P24-L21** | Agent MCP scope | Agent uses MCP for incident **read and write:** `get`, `list`, `create`, `update_status`, `summary` — **no direct HTTP to `/incidents`** |
| **P24-L22** | Agent MCP token scopes | Minted tokens include **`incidents:read` + `incidents:write`** for authorized callers |
| **P24-L23** | Write graph path | New intent **`incident_write`** → node **`mutate_incident`** → generate \| fallback; priority: `incident_write` > `both` > `incident` > `inventory` > `rag` |

Write confirmations use **template answers** (exact IDs/statuses) — not LLM paraphrase (see P24-OPT-J6).

---

## Locked decisions — Ops UX stretch (same PR, compliant with ticket)

Stretch items are **beyond minimum grading** but **do not violate** ticket requirements. Ship in the same PR as core P24.

### Gap 2 — Incidents parsing (P24-OPT-G, Option A)

| ID | Choice |
| -- | ------ |
| **P24-OPT-G** | Same PR as P24-3/3b; implement on **MCP + classifier** — not legacy `incidents.py` |
| **P24-OPT-G1** | MCP `action=summary` → `GET /incidents/summary`; classifier signals for aggregate questions |
| **P24-OPT-G2** | **`category`** on list filters (classifier + MCP `list`) — supersedes P2-L20 defer for agent/MCP path |
| **P24-OPT-G3** | Relaxed **`#N` routing** — `#42` / `status of #42` → incident read without requiring "incident" noun (guard KB-only phrasing) |
| **P24-OPT-G4** | Fuzzy branch aliases — **deferred** unless manual testing shows misses |

### Gap 3 — Inventory write messaging (P24-OPT-H, Option A)

| ID | Choice |
| -- | ------ |
| **P24-OPT-H1** | Agent detects inventory **write verbs** (`restock`, `inbound`, `outbound`, `adjust`, `create product`, etc.) |
| **P24-OPT-H2** | Short-circuit to fallback — **no HTTP fetch** |
| **P24-OPT-H3** | MCP `query_inventory` keeps explicit **`INVENTORY_WRITE_FORBIDDEN`** |

### Gap 4 — Compound questions (P24-OPT-I, Option C — deferred)

| ID | Choice |
| -- | ------ |
| **P24-OPT-I** | Incident + inventory in **one question** out of scope — keep P2-L15 (`both` = incident + KB only) |
| **P24-OPT-I1** | Document as known limit; optional `/support` UI tip: ask one topic per question |

### Gap 5 — Classifier mis-routes (P24-OPT-F, Option A)

| ID | Choice |
| -- | ------ |
| **P24-OPT-F1** | **Procedure-first guard** → `rag` when procedure phrasing (`how do I`, `what should we`, `procedure`, `policy`, …) without live-data signals |
| **P24-OPT-F2** | *"How do I create an incident"* → `rag`; *"Create incident for broken POS…"* → `incident_write` |
| **P24-OPT-F3** | Tests in `test_classify.py` for policy vs live inventory/incident |

### Gap 6 — Generation context (P24-OPT-J, Option A)

| ID | Choice |
| -- | ------ |
| **P24-OPT-J1** | Prepend **scope header** to tool context before generation |
| **P24-OPT-J2** | Inventory: `scope=location_id:N (Brasaland …)` |
| **P24-OPT-J3** | Incidents: `filters=status=…, branch=…, category=…` when present |
| **P24-OPT-J4** | Cap list rows at **10**; note truncation when applicable |
| **P24-OPT-J5** | `SUPPORT_SYSTEM_PROMPT`: state location/filter scope in first sentence when operational data includes it |
| **P24-OPT-J6** | Write confirmations: **template answers** only |

### Inventory ops hardening (P24-OPT-A–E)

| ID | Choice |
| -- | ------ |
| **P24-OPT-L1** | Default **`location_id=1`** when product/SKU present but location omitted (`AGENT_DEFAULT_LOCATION_ID`, default `1`) |
| **P24-OPT-L2** | No SKU/name → do **not** fetch full catalog; clarifying fallback |
| **P24-OPT-L3** | Name match → cap at **5 rows** or disambiguation list |
| **P24-OPT-L4** | Shared Python location map (ids 1–14) in `packages/shared/restaurant_locations.py` |
| **P24-OPT-A** | Forgiving hint extraction + tests (`id#4`, Chapinero, loose SKU) |
| **P24-OPT-B** | Safe defaults, row cap, fallback templates |
| **P24-OPT-C** | Scope labels in generation *(merged with P24-OPT-J2)* |
| **P24-OPT-D** | `/support` placeholder + collapsible tips |
| **P24-OPT-E** | Optional `GET /inventory/products?name=` — only if fetch-all still too slow |

---

## Architecture

```
┌─────────────────┐     OAuth 2.1        ┌──────────────────────────┐
│ MCP Playground  │ ───────────────────► │  mcps/brasaland-company- │
│ External agent  │     Bearer token     │  tools (FastMCP HTTP)     │
└─────────────────┘                      │  + mcpauth verifier       │
                                         └────────────┬─────────────┘
┌─────────────────┐     mint + Bearer               │ HTTP + user JWT
│ /agent/query    │ ──► langchain-mcp-adapters ─────►│
│ (LangGraph)     │     incidents via MCP only       ▼
│                 │     inventory via direct HTTP    ┌──────────────────────────┐
└─────────────────┘     (P24-L5)                     │  FastAPI (existing)       │
                                                    │  /incidents  /inventory   │
                                                    └──────────────────────────┘
```

MCP server **relies on** incidents and inventory modules — it does **not** replace them.

---

## MCP server layout

| Responsibility | Location |
| -------------- | -------- |
| MCP server entry | `mcps/brasaland-company-tools/src/brasaland_mcp/server.py` |
| Incidents tool | `mcps/brasaland-company-tools/src/brasaland_mcp/tools/incidents.py` |
| Inventory tool | `mcps/brasaland-company-tools/src/brasaland_mcp/tools/inventory.py` |
| mcpauth wiring | `mcps/brasaland-company-tools/src/brasaland_mcp/auth.py` |
| Error codes | `mcps/brasaland-company-tools/src/brasaland_mcp/errors.py` |
| Upstream HTTP | `mcps/brasaland-company-tools/src/brasaland_mcp/upstream.py` |
| Ops README | `mcps/brasaland-company-tools/README.md` |

**Dependencies** (`uv add` in `mcps/brasaland-company-tools/`): `fastmcp`, `getmcpauth-python`, `httpx`, `pydantic`.

**Agent client** (`uv add` in `services/api/`): `langchain-mcp-adapters`.

---

## Authentication & security

### mcpauth resource-server mode

- Mount **protected resource metadata** (RFC 9728).
- Validate JWTs via getmcpauth **introspection**.
- Reject unauthenticated `tools/list` and `tools/call` with spec-correct **401** + `WWW-Authenticate`.
- **Do not** use FastMCP built-in auth as primary layer.

### Token flows

| Client | Token |
| ------ | ----- |
| MCP Playground (Codespaces) | OAuth against getmcpauth.dev; use **public forwarded URL** |
| Support agent | Validate existing JWT → mint MCP token → call MCP server |

### Scope matrix

| Tool / action | Scope |
| ------------- | ----- |
| `get`, `list`, `summary` | `incidents:read` |
| `create`, `update_status` | `incidents:write` |
| `query_inventory` | `inventory:read` |

### Error codes

| Code | HTTP | When |
| ---- | ---- | ---- |
| `AUTH_MISSING` | 401 | No Authorization header |
| `AUTH_INVALID` | 401 | Token failed introspection |
| `AUTHZ_INSUFFICIENT_SCOPE` | 403 | Valid token, missing scope |
| `VALIDATION_ERROR` | 422 | Invalid tool input |
| `INVENTORY_WRITE_FORBIDDEN` | 403 | Write attempt on inventory tool |
| `UPSTREAM_NOT_FOUND` | 404 | FastAPI 404 |
| `UPSTREAM_ERROR` | 502 | FastAPI 5xx / transport failure |

---

## Tool contracts

### `manage_incident_tickets`

**Description:** Create, update status, query, or summarize Brasaland incident tickets. Write actions require `incidents:write`; read actions require `incidents:read`. Status updates follow lifecycle rules enforced by the Incidents Manager API (`open` → `in_progress` → `resolved` | `discarded`).

**Input schema:**

```json
{
  "action": "create | update_status | get | list | summary",
  "incident_id": "integer — required for get, update_status",
  "status": "open | in_progress | resolved | discarded — required for update_status",
  "filters": {
    "status": "optional — list",
    "origin": "customer | branch | internal",
    "branch": "canonical slug e.g. miami_doral",
    "category": "equipment_failure | supply_issue | …"
  },
  "payload": {
    "title": "required for create",
    "description": "required for create",
    "category": "required for create",
    "origin": "required for create",
    "branch": "required for create",
    "status": "optional on create, default open"
  }
}
```

**Upstream mapping:**

| action | HTTP |
| ------ | ---- |
| `create` | `POST /incidents` |
| `update_status` | `PATCH /incidents/{id}/status` — body `{"status": "…"}` |
| `get` | `GET /incidents/{id}` |
| `list` | `GET /incidents?status=&origin=&branch=&category=` |
| `summary` | `GET /incidents/summary` |

---

### `query_inventory`

**Description:** **Read-only** inventory queries (products, stock, thresholds). Cannot create products, adjust stock, or submit orders. Write attempts return `INVENTORY_WRITE_FORBIDDEN`.

**Input schema:**

```json
{
  "action": "query",
  "product_id": "optional integer",
  "sku": "optional string",
  "location_id": "optional integer 1–14",
  "name": "optional partial product name"
}
```

**Write rejection:** If `action` ≠ `query` or input contains write keywords (`create`, `update`, `delete`, `inbound`, `outbound`, `adjust`, `restock`, `patch`), return `INVENTORY_WRITE_FORBIDDEN`.

**Upstream:** `GET /inventory/products` or `GET /inventory/products/{id}?location_id=N` only.

---

## Agent migration & graph delta

### Incidents — MCP client (replaces direct HTTP)

| Before | After |
| ------ | ----- |
| `lookup_incident_node` → `lookup_incidents()` in `incidents.py` | `lookup_incident_node` → MCP `manage_incident_tickets` (read actions) |
| *(none)* | `mutate_incident_node` → MCP `manage_incident_tickets` (create, update_status) |

**Delete:** `services/api/agent/tools/incidents.py`

**Add:** `services/api/agent/mcp_client.py` — MCP client, token mint, envelope mapping

### Inventory — unchanged (P24-L5)

`lookup_inventory_stock_node` → `agent/tools/inventory.py` → direct HTTP + OPT hardening

### Edge routing delta

| Intent | Sequence |
| ------ | -------- |
| `rag` | `classify → retrieve → generate \| refuse` *(unchanged)* |
| `incident` | `classify → lookup_incident → generate \| fallback` *(unchanged)* |
| `incident_write` | `classify → mutate_incident → generate \| fallback` *(new)* |
| `both` | `classify → lookup_incident → retrieve → generate \| fallback` *(unchanged)* |
| `inventory` | `classify → lookup_inventory_stock → generate \| fallback` *(unchanged)* |

### Classifier priority

```
incident_write > both > incident > inventory > rag
```

Apply **P24-OPT-F** procedure guard before tool intents.

---

## Environment variables

```bash
# --- MCP server (context-24) ---
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8765
MCP_INTERNAL_API_BASE_URL=http://127.0.0.1:8000
MCPAUTH_ISSUER_URL=https://getmcpauth.dev
MCPAUTH_REGISTRATION_SECRET=
MCP_RESOURCE_SERVER_URL=http://127.0.0.1:8765

# --- Agent MCP client (context-24) ---
AGENT_MCP_SERVER_URL=http://127.0.0.1:8765

# --- Agent tools (existing + OPT) ---
AGENT_TOOL_TIMEOUT_SECONDS=5
AGENT_INTERNAL_API_BASE_URL=http://127.0.0.1:8000
AGENT_DEFAULT_LOCATION_ID=1
```

---

## Implementation phases (single PR)

| Phase | Deliverable | Exit check |
| ----- | ----------- | ---------- |
| **P24-0** | `mcps/` uv scaffold | Server starts on `MCP_SERVER_PORT` |
| **P24-1** | mcpauth + FastMCP HTTP + error codes + logging | Unauthenticated `tools/list` → 401 |
| **P24-2** | Both MCP tools + summary/category + inventory write rejection | Playground: one flow per tool; write rejection documented |
| **P24-3** | Agent read via MCP; delete `incidents.py` | No direct incidents HTTP; read routing evals pass |
| **P24-3b** | Agent write via MCP + OPT-G + OPT-F classifier | Create/update via MCP; summary/category/#42 work |
| **P24-OPT** | Inventory A/B, OPT-H/J/D; agent fallbacks | Inventory UX + write guard + scope labels |
| **P24-UX** | Natural-language classifier, inventory name hints, UI chips | Plural/list incidents, smarter refuse, `/support` examples |
| **P24-4** | Tests, README, `.env.example` | Verification checklist green |

**Playground:** Forward Codespaces port publicly; paste URL into MCP Playground — localhost alone will not work.

---

## Verification checklist (evaluation criteria)

### MCP server (required)

- [x] Server under `mcps/`, starts, exposes tools via MCP discovery
- [x] Client without valid OAuth token cannot list or execute tools
- [x] `manage_incident_tickets`: create, PATCH status, get, list, summary on real API *(unit + manual with upstream JWT)*
- [x] `query_inventory`: reads work; write attempt → `INVENTORY_WRITE_FORBIDDEN`
- [x] Tool descriptions/schemas sufficient from discovery alone
- [x] Auth / authz / validation errors: distinct codes and messages
- [x] ≥1 log entry per tool invocation (client, tool, result)

### Agent migration (required)

- [x] Agent never calls incidents manager directly — all incident ops via MCP
- [x] `agent/tools/incidents.py` deleted
- [x] RAG vs tool routing preserved for read paths

### Playground (required)

- [x] Tested with public Codespaces forwarded URL *(public URL live; OAuth metadata + authenticated tools/list + write rejection verified; incidents list/summary E2E with upstream JWT)*

### Stretch (same PR, optional for grade)

- [x] Agent create/update incidents via MCP (P24-L21)
- [x] OPT-G/F/H/J and inventory OPT tests pass
- [x] Known limit documented: no compound incident+inventory in one question (P24-OPT-I)

---

## Known limits & non-goals

- **Compound incident + inventory** in one question — out of scope (P24-OPT-I)
- **Fuzzy branch aliases** — deferred (P24-OPT-G4); partial natural-language fixes in P24-UX
- **Person / assignee search on incidents** — no schema field; deferred
- **Branch vs inventory location ids** — different taxonomies; no bridge yet
- Replace incidents/inventory repository logic inside MCP
- FastMCP built-in OAuth as primary auth
- Migrate inventory agent node to MCP
- stdio transport for production validation
- MCP access to suppliers, reporting, knowledge, telemetry, tasks
- Direct HTTP to `/incidents` from agent under any circumstance

---

## Criteria coverage matrix

| Criterion | Phase |
| --------- | ----- |
| mcps/ + discovery | P24-0, P24-1 |
| OAuth protection | P24-1 |
| Incidents tool | P24-2 |
| Inventory read + write rejection | P24-2 |
| Error codes + logging | P24-1, P24-2 |
| Agent MCP migration | P24-3, P24-3b |
| Playground | P24-2 |
| Ops UX stretch | P24-OPT |

---

## MCP access scope

| Domain | MCP | Support agent |
| ------ | --- | ------------- |
| **Incidents** | read + write | read + write via MCP |
| **Inventory** | read-only | read-only via direct HTTP |
| **All other domains** | not exposed | RAG or N/A |

---

_Locked decisions finalized 2026-08-01. Extends context-23 P2 for incidents transport; inventory agent path unchanged._
