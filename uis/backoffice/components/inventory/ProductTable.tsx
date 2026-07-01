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
import { Product } from "@/types/inventory";

interface ProductTableProps {
  products: Product[];
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
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
}: ProductTableProps): React.JSX.Element {
  if (error) {
    return <ErrorState message={error} onRetry={onRetry} showHomeLink={false} />;
  }

  return (
    <section className="overflow-hidden rounded-xl border border-amber-200/20 bg-stone-900/85">
      <div className="border-b border-amber-200/10 px-4 py-3 text-xs text-stone-400">
        {loading
          ? "Loading products..."
          : `${products.length} product${products.length === 1 ? "" : "s"}`}
      </div>

      {loading ? (
        <p className="px-4 py-8 text-sm text-stone-400">Fetching live stock from the API…</p>
      ) : products.length === 0 ? (
        <p className="px-4 py-8 text-sm text-stone-400">No products in the catalogue yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-stone-950/60 text-xs uppercase tracking-[0.08em] text-stone-400">
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
            <tbody className="divide-y divide-stone-800/80">
              {products.map((product) => {
                const level = getStockLevel(product.current_stock);
                return (
                  <tr key={product.id} className="text-stone-200">
                    <td className="px-4 py-3 font-medium text-amber-50">{product.name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-stone-400">{product.sku}</td>
                    <td className="px-4 py-3">
                      {CATEGORY_LABELS[product.category] ?? product.category}
                    </td>
                    <td className="px-4 py-3">
                      {COUNTRY_LABELS[product.country] ?? product.country}
                    </td>
                    <td className="px-4 py-3 font-semibold text-amber-100">
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
                          href={`/inventory/orders/inbound?productId=${product.id}`}
                          className="rounded-full border border-emerald-400/50 px-3 py-1 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-500/10"
                        >
                          Log inbound
                        </Link>
                        <Link
                          href={`/inventory/orders/outbound?productId=${product.id}`}
                          className="rounded-full border border-amber-400/50 px-3 py-1 text-xs font-semibold text-amber-200 transition hover:bg-amber-500/10"
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
