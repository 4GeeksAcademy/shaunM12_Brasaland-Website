/**
 * Stock level thresholds for inventory dashboards.
 *
 * Prefer ``min_stock_threshold`` from the API (resolved per restaurant when
 * ``location_id`` is set). ``LOW_STOCK_THRESHOLD`` is the UI fallback when the
 * API value is unavailable.
 */
export const LOW_STOCK_THRESHOLD = 10;

export type StockLevel = "healthy" | "low" | "out";

export function getStockLevel(
  currentStock: number,
  minStockThreshold: number = LOW_STOCK_THRESHOLD,
): StockLevel {
  if (currentStock <= 0) {
    return "out";
  }
  if (currentStock <= minStockThreshold) {
    return "low";
  }
  return "healthy";
}

export const STOCK_LEVEL_LABELS: Record<StockLevel, string> = {
  healthy: "Healthy",
  low: "Low stock",
  out: "Out of stock",
};

export const STOCK_LEVEL_CLASSES: Record<StockLevel, string> = {
  healthy: "bo-badge-healthy rounded-full px-2 py-0.5 text-xs font-semibold",
  low: "bo-badge-warn rounded-full px-2 py-0.5 text-xs font-semibold",
  out: "bo-badge-danger rounded-full px-2 py-0.5 text-xs font-semibold",
};
