/**
 * URL parameter conventions for the backoffice:
 * - Browser address bar / Next.js pages: camelCase (`productId`, `locationId`, …)
 * - FastAPI query strings: snake_case (`location_id`, `week_start`, …)
 *
 * Translation belongs in this module and in `lib/*` API clients — not in page JSX.
 */

/** Browser-facing inventory order prefill keys (context-12). */
export const INVENTORY_PREFILL_PARAMS = {
  productId: "productId",
  locationId: "locationId",
} as const;

export interface InventoryPrefill {
  productId: string | null;
  locationId: string | null;
}

export function readInventoryPrefill(
  searchParams: Pick<URLSearchParams, "get">,
): InventoryPrefill {
  return {
    productId: searchParams.get(INVENTORY_PREFILL_PARAMS.productId),
    locationId: searchParams.get(INVENTORY_PREFILL_PARAMS.locationId),
  };
}

export function buildInventoryOrderPrefillQuery(
  productId: number,
  locationId?: number,
): string {
  const params = new URLSearchParams();
  params.set(INVENTORY_PREFILL_PARAMS.productId, String(productId));
  if (locationId != null) {
    params.set(INVENTORY_PREFILL_PARAMS.locationId, String(locationId));
  }
  return params.toString();
}

export function inventoryOrderPrefillHref(
  orderType: "inbound" | "outbound",
  productId: number,
  locationId?: number,
): string {
  const query = buildInventoryOrderPrefillQuery(productId, locationId);
  return `/inventory/orders/${orderType}?${query}`;
}

/** camelCase fetch options → snake_case FastAPI query string for inventory products. */
export function buildInventoryProductsApiQuery(options?: {
  locationId?: number;
  includeInactive?: boolean;
}): string {
  const params = new URLSearchParams();
  if (options?.locationId != null) {
    params.set("location_id", String(options.locationId));
  }
  if (options?.includeInactive) {
    params.set("include_inactive", "true");
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

/** camelCase week selector → snake_case FastAPI query string for reporting KPIs. */
export function buildReportingWeekStartApiQuery(weekStart?: string | null): string {
  if (!weekStart?.trim()) {
    return "";
  }
  return `?week_start=${encodeURIComponent(weekStart.trim())}`;
}
