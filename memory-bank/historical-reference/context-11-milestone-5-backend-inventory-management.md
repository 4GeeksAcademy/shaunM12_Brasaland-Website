# CONTEXT — Milestone 5: Backend Inventory Management · Brasaland

## AI Engineering - 4Geeks Academy

> **Ticket:** BRD-0512 — Centralised ingredient inventory API
> **Repository index:** `context-11-milestone-5-backend-inventory-management.md`
> **Historical path:** `05-backend-inventory-orm/CONTEXT-brasaland.md`
> **Type:** New feature (inventory layer)
> **Status:** 🟢 Implemented (backend inventory API + tests)

### Locked decisions

- **Dual database architecture (required):** The FastAPI app connects to **two
  databases simultaneously** for the lifetime of the process:
  - **TinyDB** (existing JSON stores) — users, auth, suppliers, and all
    pre-milestone features. Access via `database.get_*_table()` and existing
    repositories; **do not migrate these off TinyDB in this milestone**.
  - **Supabase/PostgreSQL** (new) — ingredients (products), inbound orders,
    outbound orders, and all stock-related history. Access via
    `database.get_db()` (`Depends`) and SQLModel.
- **Persistence split:** Products and stock quantities live in **Supabase only**.
  Stock must **not** be a directly editable column — it is always derived from
  order history (inbound increases, outbound decreases).
- **Cross-database user reference:** Inbound and outbound orders in Supabase store
  `user_uuid` referencing the authenticated TinyDB user. **No User table is
  replicated in Supabase** (store `str(current_user.id)`; TinyDB users use
  integer ids today).
- **ORM vs API schemas:** SQLModel tables in `inventory/models.py`; Pydantic
  request/response types in `inventory/schemas.py` (**separate files, separate
  classes**). **Never return a raw ORM object from an endpoint** — always map
  to a response schema (including computed `current_stock`).
- **Router:** All inventory routes under `/inventory` using a **dedicated
  `APIRouter`** in `inventory/routes.py`, registered once in `main.py`.
- **Foreign keys:** `ingredient_id` FK relationships must be **enforced at the
  database level** in Supabase (SQLModel `ForeignKey` + `create_all` / migrations).
- **Locations** are integers `1–14` only — no Location model or FK this milestone.
- **Auth:** Product creation and inbound/outbound order creation require
  authentication; persist the authenticated user's id as `user_uuid` on orders.

---

## Focus

Brasaland has 14 locations across Colombia and Florida but no central view of
ingredient stock. Kitchens still run on WhatsApp and spreadsheets. This
milestone delivers the **ingredient inventory API**: deliveries increase stock,
consumption/waste decrease it, and `current_stock` is always the net balance.

> **From Nicolás (CTO) — Notion #BRD-0512:**
> "The operations team is going in blind on ingredients. Felipe's supervisors
> don't know how much beef is available in Miami until they call the kitchen.
> Build the inventory API. Ingredient entries come from supplier deliveries;
> exits come from consumption logs and waste reports. Stock must be read-only —
> it's always the net of what arrived minus what was used. All endpoints under
> `/inventory`."

> **From Tech Lead — Milestone 5 PRD (dual database + inventory ORM):**
> The FastAPI app connects to two databases simultaneously: TinyDB (existing,
> for users and auth) and Supabase (new, for inventory and orders). Products and
> stock quantities live in Supabase. Stock must not be a directly editable
> column — it is always derived from order history. Inbound orders increase
> stock; outbound orders decrease it. Both are stored in Supabase and reference
> the user UUID from TinyDB — no user table is replicated in Supabase. ORM
> models use SQLModel. Pydantic schemas for request and response are in a
> separate file from ORM models — never return a raw ORM object from an
> endpoint. All inventory routes must be registered under the `/inventory` prefix
> using a dedicated `APIRouter`. Entity names, field constraints, and business
> rules in this document are company-specific and authoritative.

---

## Dual database architecture

Both connections must be **active and correctly used** in the same running app.
There is no feature flag that disables TinyDB when Supabase is configured.

| Concern | Database | Access pattern | Examples |
| ------- | -------- | -------------- | -------- |
| Users, sessions, auth tokens | TinyDB (`users.json`, `auth.json`) | `database.get_users_table()`, `auth/*` | Login, `get_current_user` |
| Suppliers (pre-existing) | TinyDB (`suppliers.json`) | `database.get_suppliers_table()` | Supplier directory |
| Ingredients / products | Supabase | `Depends(get_db)` + SQLModel | `Ingredient` |
| Inbound / outbound orders | Supabase | `Depends(get_db)` + SQLModel | `IngredientEntry`, `IngredientExit` |
| Stock balance | **Computed** (Supabase queries) | Repository aggregation | `current_stock` on responses |

**Connection wiring (already in repo):**

- TinyDB — `database.py` lazy singletons (`get_users_db()`, `get_auth_db()`, …).
- Supabase — `config.DATABASE_URL` → `database.get_engine()` → `database.get_db()`
  (one SQLModel `Session` per request; no global session variable).

**Rules of the road:**

1. Inventory routes talk to Supabase **only** through `get_db` / repository layer.
2. Auth resolves the current user from TinyDB **before** writing orders to
   Supabase; stamp `user_uuid` on the order row.
3. Do not add inventory tables to TinyDB or user tables to Supabase.
4. Do not expose endpoints that PATCH/PUT a `stock` or `current_stock` field.

---

## Entity specification

Use these **canonical names** in code. README aliases are noted once for
mapping only.

| Canonical name    | README alias    | Role                         |
| ----------------- | --------------- | ---------------------------- |
| `Ingredient`      | `Product`       | Catalogue item               |
| `IngredientEntry` | `InboundOrder`  | Supplier delivery (stock in) |
| `IngredientExit`  | `OutboundOrder` | Consumption or waste (out)   |

### `Ingredient`

| Field           | Type       | Notes |
| --------------- | ---------- | ----- |
| `id`            | `int` (PK) | Auto-increment |
| `name`          | `str`      | e.g. `"Beef brisket"`, `"Takeaway box (M)"` |
| `sku`           | `str`      | Unique, e.g. `"BRS-BEEF-001"` |
| `unit`          | `str`      | `"kg"`, `"litre"`, `"unit"` |
| `category`      | `str`      | `"meat"`, `"produce"`, `"sauce"`, `"beverage"`, `"packaging"`, `"cleaning"` |
| `country`       | `str`      | `"CO"` or `"US"` |
| `current_stock` | `float`    | **Response only — computed, not stored** |

### `IngredientEntry` (inbound)

| Field           | Type                    | Notes |
| --------------- | ----------------------- | ----- |
| `id`            | `int` (PK)              | Auto-increment |
| `ingredient_id` | `int` (FK → Ingredient) | |
| `quantity`      | `float`                 | In ingredient's unit |
| `supplier_name` | `str`                   | Supplier for this delivery |
| `location_id`   | `int`                   | Receiving location (1–14), not FK |
| `created_at`    | `datetime`              | Auto-set |
| `user_uuid`     | `str`                   | Supervisor who logged it (TinyDB user ref) |

### `IngredientExit` (outbound)

| Field           | Type                    | Notes |
| --------------- | ----------------------- | ----- |
| `id`            | `int` (PK)              | Auto-increment |
| `ingredient_id` | `int` (FK → Ingredient) | |
| `quantity`      | `float`                 | Amount consumed or wasted |
| `reason`        | `str`                   | **`"consumption"` or `"waste"` only** |
| `location_id`   | `int`                   | Location (1–14), not FK |
| `created_at`    | `datetime`              | Auto-set |
| `user_uuid`     | `str`                   | Staff who logged it (TinyDB user ref) |

---

## Business rules

1. **`current_stock` is computed:**
   `SUM(IngredientEntry.quantity) − SUM(IngredientExit.quantity)` per
   ingredient.
2. **New ingredients start at zero stock** — stock only changes via
   inbound/outbound orders.
3. **Reject negative stock** before persisting an exit. Return `HTTP 400`:
   `"Insufficient stock for ingredient '{name}'. Available: {available}, requested: {requested}."`
4. **CO and US ingredients share one table** — filter by `country` when needed.
5. **No User model in Supabase** — `user_uuid` references TinyDB users only.
6. **Inbound/outbound POST requires auth** — set `user_uuid` from
   `get_current_user` (string form of user id).
7. **No direct stock mutation** — there is no API to set or patch stock; the
   only way stock changes is by creating inbound or outbound order rows.
8. **Endpoints return schemas, not ORM instances** — map SQLModel rows to
   Pydantic response models in the router or repository before returning.

---

## API (`/inventory`)

| Method | Path                         | Auth | Description |
| ------ | ---------------------------- | ---- | ----------- |
| `GET`  | `/inventory/products`        | —    | List ingredients with `current_stock` |
| `POST` | `/inventory/products`        | ✅   | Create ingredient |
| `GET`  | `/inventory/products/{id}`   | —    | One ingredient + `current_stock` |
| `POST` | `/inventory/orders/inbound`  | ✅   | Log delivery (`IngredientEntry`) |
| `POST` | `/inventory/orders/outbound` | ✅   | Log consumption/waste (`IngredientExit`) |
| `GET`  | `/inventory/orders`          | —    | List entries and exits with ingredient data |

> **Note:** API paths use `products` / `orders` per the ticket; domain models use
> `Ingredient` / `IngredientEntry` / `IngredientExit`.

---

## File structure (this repo)

Align with existing `services/api/` packages (`auth/`, `suppliers/`, `users/`),
not a flat `services/routers/` tree:

```text
services/api/
├── main.py                 # register inventory router; create_all on startup
├── database.py             # TinyDB (existing) + get_engine() + get_db() session
├── config.py               # DATABASE_URL (existing)
└── inventory/
    ├── __init__.py
    ├── models.py           # SQLModel: Ingredient, IngredientEntry, IngredientExit
    ├── schemas.py          # Pydantic request/response (incl. current_stock on product response)
    ├── routes.py           # APIRouter — mount at /inventory
    ├── repository.py       # stock queries, order persistence, negative-stock check
    └── seed.py             # dev seed data (or extend services/api/seed.py)
```

**Startup:** call `SQLModel.metadata.create_all(get_engine())` in the FastAPI
`lifespan` (after engine is available).

---

## Implementation checklist

### SQLModel — `inventory/models.py`

- `Ingredient` — `table=True`; fields: `id`, `name`, `sku`, `unit`,
      `category`, `country` (no `current_stock` column).
- `IngredientEntry` — FK `ingredient_id` → `Ingredient.id` with database-level
      `ForeignKey` constraint; `quantity`, `supplier_name`, `location_id`,
      `created_at`, `user_uuid`.
- `IngredientExit` — FK `ingredient_id` → `Ingredient.id` with database-level
      `ForeignKey` constraint; `quantity`, `reason`, `location_id`, `created_at`,
      `user_uuid`.
- `create_all(engine)` on app startup (creates tables + FK constraints in
      Supabase).

### Pydantic — `inventory/schemas.py`

- Separate request/response schemas for product, inbound order, outbound
      order.
- Product **response** includes computed `current_stock`.
- Outbound request validates `reason` ∈ `{"consumption", "waste"}`.
- **Never return raw SQLModel instances** from route handlers — always
      `model_validate` / explicit mapping to response schemas.

### Router — `inventory/routes.py`

- **Dedicated** `APIRouter(tags=["inventory"])`, mounted in `main.py` with
      `prefix="/inventory"` (all six routes live under this prefix).
- Implement all six endpoints per table above.
- Inbound/outbound: `Depends(get_current_user)` (TinyDB auth) +
      `Depends(get_db)` (Supabase session).
- Negative-stock guard on outbound before `commit`.
- Product create: `Depends(get_current_user)` + `Depends(get_db)`; product
      read/list: `Depends(get_db)` only; no stock column on write.

### Seed data (required for demo)

The canonical catalogue lives in `inventory/seed_data.py` (**99 ingredients**):
context-11 core six, Latin grill meats, seafood, produce, sauces, beverages,
packaging (boxes S/M/L, cups, lids, cutlery, napkins), and cleaning supplies.
A new **`seafood`** category is included alongside `meat`, `produce`, etc.

**Context-11 minimum (still present in seed):**

| name              | sku           | unit  | category  | country |
| ----------------- | ------------- | ----- | --------- | ------- |
| Beef brisket      | BRS-BEEF-001  | kg    | meat      | CO      |
| Pork ribs         | BRS-PORK-001  | kg    | meat      | US      |
| Chimichurri sauce | BRS-SAUCE-001 | litre | sauce     | CO      |
| House BBQ sauce   | BRS-SAUCE-002 | litre | sauce     | US      |
| Yuca (cassava)    | BRS-PROD-001  | kg    | produce   | CO      |
| Takeaway box (M)  | BRS-PKG-001   | unit  | packaging | CO      |

**Demo orders:** context-11 inbound/outbound on beef, pork, and chimichurri
(beef net stock **50 kg** for tests). Remaining SKUs are auto-seeded for UI
demos: **~81 healthy**, **~10 low** (≤10 units), **~8 out** (see
`OUT_OF_STOCK_SKUS` / `LOW_STOCK_INBOUND` in `seed_data.py`).

**Full reset (dev):** from repo root, `npm run api:inventory-seed` — wipes
Supabase inventory tables and reloads the catalogue (requires `DATABASE_URL`).

---

## Acceptance criteria (evaluator)

### Tech Lead / PRD (milestone gate)

- **All endpoints functional** under `/inventory` (six routes in the API table).
- **Dual database:** TinyDB still serves auth/users/suppliers; Supabase serves
      inventory and orders — both connections active in one running app.
- **FK relationships enforced at database level** (`ingredient_id` →
      `Ingredient.id` on entry and exit tables).
- **No direct stock mutation** — no stored stock column; no endpoint that
      sets stock except via inbound/outbound order creation.
- **ORM/schemas separated** — `models.py` vs `schemas.py`; responses are
      Pydantic models, not raw ORM objects.
- **Dedicated inventory router** registered at `/inventory`.

### Behavioural checks

- `POST` outbound exceeding stock → `HTTP 400` with the exact
      insufficient-stock message.
- `GET /inventory/products` → `current_stock` = net of seeded entries −
      exits.
- `country` on model and product response.
- `reason` only `"consumption"` or `"waste"`.
- Inbound/outbound store authenticated `user_uuid` (TinyDB user reference).

---

## Prerequisites (already in repo)

| Piece | Location |
| ----- | -------- |
| `sqlmodel`, `psycopg2-binary` | `services/api/pyproject.toml` |
| `DATABASE_URL` | `services/api/.env` |
| TinyDB accessors (users, auth, suppliers) | `database.get_*_table()` |
| Supabase engine + session dependency | `database.get_engine()`, `database.get_db()` |
| Auth for protected routes (TinyDB-backed) | `auth.dependencies.get_current_user` |
| TinyDB users (for order `user_uuid`) | `users/` + `database.get_users_table()` |

---

## Out of scope

- Location master data / FK to locations
- User table in Supabase
- Frontend inventory UI
- Migrating auth/suppliers off TinyDB
- Stored `current_stock` column

---

_Internal document — 4Geeks Academy · AI Engineering Track · Milestone 5 · Brasaland_
