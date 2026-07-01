# CONTEXT — Milestone 5: Backoffice Inventory Management Interface · Brasaland

## AI Engineering - 4Geeks Academy

> **Ticket:** BRD-0512 (frontend) — Backoffice inventory management interface
> **Repository index:** `context-12-milestone-5-backoffice-inventory-interface.md`
> **Companion doc:** `context-11-milestone-5-backend-inventory-management.md` (API)
> **App:** `uis/backoffice` (Next.js App Router)
> **Type:** New feature (inventory UI)
> **Status:** 🟢 Implemented (backoffice inventory UI)

### Locked decisions

- **API is already shipped.** This milestone consumes the live `/inventory`
  endpoints from context-11. No backend schema or route changes unless a test
  exposes a real bug.
- **Single API module.** All inventory HTTP calls live in `lib/inventory.ts`.
  No page or component may call `fetch` against `/inventory` directly.
- **Auth transport matches the existing backoffice.** Protected API calls use
  `authorizedFetch` from `lib/http.ts`, which attaches
  `Authorization: Bearer <token>` from `localStorage` via `auth-storage.ts`.
  Unauthenticated users are redirected to `/login` by the existing
  `ProtectedShell` / `AuthGuard` pattern — do not invent a parallel guard.
- **Errors are user-visible.** On `4xx` or `5xx`, parse the response body with
  `formatApiError` (same as `suppliers-api.ts`) and surface the message in the
  UI. Never swallow errors silently or rely on `console.error` alone.
- **Domain naming.** API paths use `products` / `orders`; request bodies use
  `ingredient_id` per the backend. Display labels may say "product" in the UI.
- **Read-only orders history.** No delete or edit actions on the orders page.

---

## Focus

The backend team shipped the inventory API last sprint. Operations staff cannot
use Postman to log deliveries. This milestone delivers four authenticated
backoffice views that consume live API data: a stock dashboard, inbound and
outbound order forms, and a combined orders history.

> **From: Operations Manager · To: Technology Unit**
>
> The backend team shipped the inventory API last sprint — great work. Now I
> need the interface. My team can't use Postman to log deliveries.
>
> Here's what I need in the backoffice:
>
> 1. A page that shows all products with their current stock. Color-code it — I
>    want to see at a glance what is low.
> 2. A form to register an inbound order (a delivery we received).
> 3. A form to register an outbound order (a consumption or exit). It must show
>    how much stock is available before I submit, so I don't accidentally log
>    more than we have.
> 4. A read-only page showing all orders — entries and exits — with the product
>    name and who created each one.
>
> All of these pages require login. If a user is not authenticated, redirect
> them to the login page.

---

## API surface (context-11 recap)

| Method | Path | Auth (API) | Used by |
| ------ | ---- | ---------- | ------- |
| `GET` | `/inventory/products` | — | Products page, order-form product selectors |
| `POST` | `/inventory/products` | ✅ | Out of scope for this UI (no create-product form) |
| `GET` | `/inventory/products/{id}` | — | Optional; list endpoint is sufficient |
| `POST` | `/inventory/orders/inbound` | ✅ | Inbound form |
| `POST` | `/inventory/orders/outbound` | ✅ | Outbound form |
| `GET` | `/inventory/orders` | — | Orders history page |

### Product fields to display (`ProductResponse`)

`id`, `name`, `sku`, `unit`, `category`, `country`, `current_stock`

(`current_stock` is computed server-side — never editable in the UI.)

### Inbound order payload (`InboundOrderCreate`)

`ingredient_id`, `quantity`, `supplier_name`, `location_id` (integer `1–14`)

### Outbound order payload (`OutboundOrderCreate`)

`ingredient_id`, `quantity`, `reason` (`"consumption"` | `"waste"`),
`location_id` (integer `1–14`)

### Orders list shape (`OrdersListResponse`)

`inbound[]` and `outbound[]`, each row including `ingredient_name`,
`quantity`, `created_at`, `user_uuid` (plus type-specific fields).

---

## API integration layer

Create `uis/backoffice/lib/inventory.ts` as the **only** module that talks to
`/inventory`. Mirror the structure of `lib/suppliers-api.ts`:

- `getBaseUrl()` — same pattern as suppliers (optional
  `NEXT_PUBLIC_SUPPLIERS_API_BASE_URL` or a dedicated inventory env var;
  default same-origin).
- Internal `request<T>()` helper wrapping `authorizedFetch`.
- Use `authorizedFetch` for **all** inventory calls (reads and writes) so
  session expiry and token refresh behave consistently.
- On `!response.ok`, throw `new Error(formatApiError(response.status, body))`.
- Export typed functions:
  - `fetchProducts()` → `GET /inventory/products`
  - `fetchOrders()` → `GET /inventory/orders`
  - `createInboundOrder(payload)` → `POST /inventory/orders/inbound`
  - `createOutboundOrder(payload)` → `POST /inventory/orders/outbound`

Add matching TypeScript types in `uis/backoffice/types/inventory.ts`.

### Next.js proxy

Add a rewrite in `uis/backoffice/next.config.mjs` so same-origin requests work
in dev (follow the existing `/api/suppliers` pattern). Use `/api/inventory/*`
on the Next side so API calls do not collide with UI routes under `/inventory/*`:

```text
/api/inventory/:path*  →  ${apiOrigin}/inventory/:path*
```

---

## Pages

### Products — `/inventory/products`

**Route file:** `uis/backoffice/app/inventory/products/page.tsx`

- Fetch all products from `GET /inventory/products` on mount via
  `lib/inventory.ts`.
- Display a table (or card list) with entity fields: `name`, `sku`, `unit`,
  `category`, `country`, and **`current_stock`** (with unit label).
- Apply **visual stock-level indicators** (color badge, icon, or row tint):
  - **Healthy** — `current_stock` above the low threshold (green / neutral).
  - **Low** — at or below the low threshold but above zero (amber / warning).
  - **Out** — `current_stock === 0` (red / critical).
  - Document numeric thresholds in a **code comment** at the top of the
    component or in a small `lib/inventory-stock.ts` helper, e.g.
    `LOW_STOCK_THRESHOLD = 10` (same unit as the product — kg, litre, unit).
    Thresholds are a UI convention only; the API does not define them.
- Each product row includes clearly labelled links or buttons:
  - **Log inbound** → `/inventory/orders/inbound?productId={id}`
  - **Log outbound** → `/inventory/orders/outbound?productId={id}`
- Use the existing three-state UI pattern (`useApiState` + loading / error /
  empty states) as on `/suppliers`.

### Inbound order form — `/inventory/orders/inbound`

**Route file:** `uis/backoffice/app/inventory/orders/inbound/page.tsx`

- Render a form that submits to `POST /inventory/orders/inbound` via
  `createInboundOrder()` in `lib/inventory.ts`.
- **Product selector:** dropdown listing all products **by name** (value =
  `ingredient_id`). Never ask the user to type a raw ID.
  - Pre-select the product when `?productId=` is present in the URL (from the
    products page link).
- Fields: product, quantity, supplier name, location (`1–14`).
- On **success:** clear the form and show a visible confirmation message.
- On **4xx / 5xx:** display the API error message in a dedicated alert near
  the form — not only in the console.
- **Route protection:** covered by `ProtectedShell` / `AuthGuard` (redirect to
  `/login` when unauthenticated).

### Outbound order form — `/inventory/orders/outbound`

**Route file:** `uis/backoffice/app/inventory/orders/outbound/page.tsx`

- Render a form that submits to `POST /inventory/orders/outbound`.
- **Product selector:** same name-based dropdown as inbound; honour
  `?productId=` query param.
- When the user selects a product, **fetch and display `current_stock`**
  reactively (read from the already-fetched products list, or refetch when
  selection changes). Show stock with unit before the quantity field.
- **Client-side UX guard:** if entered quantity exceeds displayed stock, show an
  inline warning before submit. This does not replace the API rule — the server
  still enforces the limit.
- On **HTTP 400** (insufficient stock), display the API error message inline
  near the quantity field.
- On success: clear form and show confirmation message (same pattern as
  inbound).

### Orders history — `/inventory/orders`

**Route file:** `uis/backoffice/app/inventory/orders/page.tsx`

- Fetch `GET /inventory/orders` and render a combined, read-only table.
- Merge `inbound` and `outbound` into one sortable list (by `created_at`,
  newest first) or two clearly labelled sections.
- Each row must show:
  - **Product name** (`ingredient_name`)
  - **Quantity** (with unit when available from product context)
  - **Order type** — inbound vs outbound (visual distinction: colour, icon, or
    label badge)
  - **Creation date** (`created_at`, formatted for locale)
  - **`user_uuid`** of the creator
- Inbound rows may also show `supplier_name`; outbound rows may show `reason`.
- **No delete or edit actions.**

---

## Route protection

All four inventory routes live under `/inventory/...` inside the backoffice.
They are **not** public paths — the existing stack handles protection:

| Layer | Location | Behaviour |
| ----- | -------- | --------- |
| `ProtectedShell` | `components/auth/ProtectedShell.tsx` | Non-public paths get `AuthGuard` |
| `AuthGuard` | `components/auth/AuthGuard.tsx` | Blocks render until session resolves; redirects to `/login` |
| `authorizedFetch` | `lib/http.ts` | Attaches bearer token; refreshes on `401` |

Do **not** add inventory paths to `isPublicPath` in `lib/auth-config.ts`.

---

## Navigation

Add inventory entry points to `components/backoffice-tabs.tsx`, e.g.:

- `/inventory/products` — **Inventory**

In-page links on the products view can reach inbound, outbound, and orders
history. Keep styling consistent with existing tabs (amber/stone palette).

---

## File structure (this repo)

```text
uis/backoffice/
├── next.config.mjs              # add /inventory/* rewrite
├── lib/
│   ├── inventory.ts             # sole /inventory API client
│   └── inventory-stock.ts       # optional: threshold helpers + comment
├── types/
│   └── inventory.ts             # Product, Order, payload types
├── app/
│   └── inventory/
│       ├── products/
│       │   └── page.tsx
│       └── orders/
│           ├── page.tsx         # history (read-only)
│           ├── inbound/
│           │   └── page.tsx
│           └── outbound/
│               └── page.tsx
└── components/
    └── inventory/               # optional: ProductTable, OrderForm, etc.
```

Align with existing patterns: `useApiState`, `ErrorState`, Tailwind classes
from `/suppliers` and `/incidents`.

---

## Acceptance criteria (evaluator)

- All **four views** are functional and reachable from the backoffice.
- All four pages require login; unauthenticated users are redirected to
  `/login`.
- All data comes from the **live API** via `lib/inventory.ts` — no hardcoded
  mock inventory in production paths.
- Products page shows `current_stock` with **visual low-stock indicators**
  (thresholds documented in code).
- Inbound form uses a **name-based product selector**; success clears form and
  shows confirmation; API errors are visible in the UI.
- Outbound form shows **reactive `current_stock`** on product change; client
  warning when quantity exceeds stock; API `400` insufficient-stock message
  shown inline near the quantity field.
- Orders history is **read-only** with product name, quantity, type, date, and
  `user_uuid`; inbound and outbound are visually distinct.
- **No component** calls `/inventory` except through `lib/inventory.ts`.

---

## Prerequisites (already in repo)

| Piece | Location |
| ----- | -------- |
| Inventory API (context-11) | `services/api/inventory/` |
| Bearer + refresh auth | `lib/http.ts`, `lib/auth-storage.ts` |
| Route protection shell | `components/auth/ProtectedShell.tsx` |
| API error formatting | `lib/api-error.ts` |
| Async UI state hook | `hooks/useApiState.ts` |
| Supplier API client (pattern) | `lib/suppliers-api.ts` |

---

## Out of scope

- Creating products from the UI (`POST /inventory/products`)
- Editing or deleting orders
- Location master data / map UI
- Changes to the public website (`uis/website`)
- Backend inventory changes (unless a UI test exposes a real defect)

---

_Internal document — 4Geeks Academy · AI Engineering Track · Milestone 5 · Brasaland_
