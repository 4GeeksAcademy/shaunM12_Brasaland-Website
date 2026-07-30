"use client";

import Link from "next/link";
import ErrorState from "@/components/ui/ErrorState";
import {
  CATEGORY_LABELS,
  COUNTRY_LABELS,
} from "@/lib/inventory-constants";
import {
  getStockLevel,
  STOCK_LEVEL_CLASSES,
  STOCK_LEVEL_LABELS,
} from "@/lib/inventory-stock";
import { inventoryOrderPrefillHref } from "@/lib/query-params";
import { Product } from "@/types/inventory";

interface ProductTableProps {
  products: Product[];
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
  locationId?: number;
}

function formatStock(value: number, unit: string): string {
  const formatted = Number.isInteger(value) ? String(value) : value.toFixed(1);
  return `${formatted} ${unit}`;
}

export default function ProductTable({
  products,
  loading,
  error,
  onRetry,
  locationId,
}: ProductTableProps): React.JSX.Element {
  if (error) {
    return <ErrorState message={error} onRetry={onRetry} showHomeLink={false} />;
  }

  return (
    <section className="overflow-hidden rounded-xl border border-[color:var(--bo-card-border)] bg-[color:var(--bo-card)]">
      <div className="border-b border-[color:var(--bo-panel-border)] px-4 py-3 text-xs bo-muted">
        {loading
          ? "Loading products..."
          : `${products.length} product${products.length === 1 ? "" : "s"}`}
      </div>

      {loading ? (
        <p className="px-4 py-8 text-sm bo-muted">Fetching live stock from the API…</p>
      ) : products.length === 0 ? (
        <p className="px-4 py-8 text-sm bo-muted">No products in the catalogue yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="bo-table">
            <thead className="bg-[color:var(--bo-row-bg)] text-xs uppercase tracking-[0.08em] bo-muted">
              <tr>
                <th className="px-4 py-3 font-semibold">Product</th>
                <th className="px-4 py-3 font-semibold">SKU</th>
                <th className="px-4 py-3 font-semibold">Category</th>
                <th className="px-4 py-3 font-semibold">Country</th>
                <th className="px-4 py-3 font-semibold">Stock</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[color:var(--bo-row-border)]">
              {products.map((product) => {
                const level = getStockLevel(
                  product.current_stock,
                  product.min_stock_threshold,
                );
                return (
                  <tr key={product.id} className="bo-fg-secondary">
                    <td className="px-4 py-3 font-medium text-[color:var(--bo-heading)]">{product.name}</td>
                    <td className="px-4 py-3 font-mono text-xs bo-muted">{product.sku}</td>
                    <td className="px-4 py-3">
                      {CATEGORY_LABELS[product.category] ?? product.category}
                    </td>
                    <td className="px-4 py-3">
                      {COUNTRY_LABELS[product.country] ?? product.country}
                    </td>
                    <td className="px-4 py-3 font-semibold text-[color:var(--bo-heading)]">
                      {formatStock(product.current_stock, product.unit)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${STOCK_LEVEL_CLASSES[level]}`}
                      >
                        {STOCK_LEVEL_LABELS[level]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <Link
                          href={inventoryOrderPrefillHref(
                            "inbound",
                            product.id,
                            locationId,
                          )}
                          className="bo-btn-secondary border-[color:var(--bo-badge-healthy-ring)] text-[color:var(--bo-badge-healthy-fg)] normal-case tracking-normal"
                        >
                          Log inbound
                        </Link>
                        <Link
                          href={inventoryOrderPrefillHref(
                            "outbound",
                            product.id,
                            locationId,
                          )}
                          className="bo-btn-secondary normal-case tracking-normal"
                        >
                          Log outbound
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
