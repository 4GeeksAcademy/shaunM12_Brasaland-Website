/**
 * UI-only stock level thresholds for inventory dashboards.
 *
 * The API does not define low-stock rules — these values drive colour badges
 * on the products page only. Threshold is compared in each product's own unit
 * (kg, litre, unit, etc.).
 */
export const LOW_STOCK_THRESHOLD = 10;

export type StockLevel = "healthy" | "low" | "out";

export function getStockLevel(currentStock: number): StockLevel {
  if (currentStock <= 0) {
    return "out";
  }
  if (currentStock <= LOW_STOCK_THRESHOLD) {
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
  healthy:
    "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/40",
  low: "bg-amber-500/15 text-amber-300 ring-1 ring-amber-400/40",
  out: "bg-rose-500/15 text-rose-300 ring-1 ring-rose-400/40",
};
