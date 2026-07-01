"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import AddProductModal from "@/components/inventory/AddProductModal";
import ErrorState from "@/components/ui/ErrorState";
import {
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  COUNTRY_LABELS,
  INPUT_CLASS,
  LABEL_CLASS,
  RESTAURANT_LOCATIONS,
  formatLocationLabel,
  getLocationsForCountry,
} from "@/lib/inventory-constants";
import { updateProductActive } from "@/lib/inventory";
import {
  getStockLevel,
  STOCK_LEVEL_CLASSES,
  STOCK_LEVEL_LABELS,
} from "@/lib/inventory-stock";
import { Product, ProductCountry } from "@/types/inventory";

interface ProductCatalogProps {
  products: Product[];
  loading: boolean;
  error: string | null;
  locationId: number;
  includeInactive: boolean;
  onLocationChange: (locationId: number) => void;
  onIncludeInactiveChange: (include: boolean) => void;
  onRetry: () => void;
  onRefresh: () => void;
}

function formatStock(value: number, unit: string): string {
  const formatted = Number.isInteger(value) ? String(value) : value.toFixed(1);
  return `${formatted} ${unit}`;
}

function groupByCategory(products: Product[]): { category: string; items: Product[] }[] {
  const byCategory = new Map<string, Product[]>();
  for (const product of products) {
    const list = byCategory.get(product.category) ?? [];
    list.push(product);
    byCategory.set(product.category, list);
  }

  const ordered: { category: string; items: Product[] }[] = [];
  for (const category of CATEGORY_ORDER) {
    const items = byCategory.get(category);
    if (!items?.length) {
      continue;
    }
    ordered.push({
      category,
      items: [...items].sort((a, b) => a.sku.localeCompare(b.sku)),
    });
    byCategory.delete(category);
  }

  for (const [category, items] of byCategory) {
    ordered.push({
      category,
      items: [...items].sort((a, b) => a.sku.localeCompare(b.sku)),
    });
  }

  return ordered;
}

export default function ProductCatalog({
  products,
  loading,
  error,
  locationId,
  includeInactive,
  onLocationChange,
  onIncludeInactiveChange,
  onRetry,
  onRefresh,
}: ProductCatalogProps): React.JSX.Element {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [toggleError, setToggleError] = useState<string | null>(null);

  const selectedLocation = RESTAURANT_LOCATIONS.find(
    (location) => location.id === locationId,
  );
  const grouped = useMemo(() => groupByCategory(products), [products]);

  const handleToggleActive = async (product: Product): Promise<void> => {
    setToggleError(null);
    setTogglingId(product.id);
    try {
      await updateProductActive(product.id, !product.is_active, locationId);
      onRefresh();
    } catch (caught) {
      setToggleError(
        caught instanceof Error ? caught.message : "Could not update catalogue status.",
      );
    } finally {
      setTogglingId(null);
    }
  };

  if (error) {
    return <ErrorState message={error} onRetry={onRetry} showHomeLink={false} />;
  }

  return (
    <>
      <section className="space-y-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
          <label className="block w-full sm:max-w-md">
            <span className={LABEL_CLASS}>Restaurant</span>
            <select
              value={locationId}
              onChange={(event) => onLocationChange(Number(event.target.value))}
              className={INPUT_CLASS}
            >
              {(["CO", "US"] as ProductCountry[]).map((country) => (
                <optgroup key={country} label={COUNTRY_LABELS[country]}>
                  {getLocationsForCountry(country).map((location) => (
                    <option key={location.id} value={location.id}>
                      {location.name} — {location.city}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>

          <div className="flex flex-wrap items-center gap-3">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-stone-300">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(event) => onIncludeInactiveChange(event.target.checked)}
                className="rounded border-stone-600 bg-stone-900 text-amber-500 focus:ring-amber-400"
              />
              Show discontinued
            </label>
            <button
              type="button"
              onClick={() => setAddModalOpen(true)}
              className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500"
            >
              Add product
            </button>
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-amber-200/20 bg-stone-900/85">
          <div className="border-b border-amber-200/10 px-4 py-3 text-xs text-stone-400">
            {loading
              ? "Loading products..."
              : selectedLocation
                ? `${products.length} product${products.length === 1 ? "" : "s"} at ${formatLocationLabel(locationId)}`
                : `${products.length} product${products.length === 1 ? "" : "s"}`}
          </div>

          {toggleError ? (
            <p className="border-b border-rose-400/20 bg-rose-500/10 px-4 py-2 text-sm text-rose-200">
              {toggleError}
            </p>
          ) : null}

          {loading ? (
            <p className="px-4 py-8 text-sm text-stone-400">
              Fetching live stock for this restaurant…
            </p>
          ) : products.length === 0 ? (
            <p className="px-4 py-8 text-sm text-stone-400">
              No products for this restaurant
              {includeInactive ? "" : " (try showing discontinued items)"}.
            </p>
          ) : (
            <div className="overflow-x-auto">
              {grouped.map(({ category, items }) => (
                <div key={category}>
                  <div className="bg-stone-950/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.1em] text-amber-200/80">
                    {CATEGORY_LABELS[category] ?? category}
                  </div>
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-stone-950/40 text-xs uppercase tracking-[0.08em] text-stone-500">
                      <tr>
                        <th className="px-4 py-2 font-semibold">Product</th>
                        <th className="px-4 py-2 font-semibold">SKU</th>
                        <th className="px-4 py-2 font-semibold">Stock @ site</th>
                        <th className="px-4 py-2 font-semibold">Stock level</th>
                        <th className="px-4 py-2 font-semibold">Catalog</th>
                        <th className="px-4 py-2 font-semibold">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-800/80">
                      {items.map((product) => {
                        const level = getStockLevel(product.current_stock);
                        return (
                          <tr
                            key={product.id}
                            className={`text-stone-200 ${!product.is_active ? "opacity-70" : ""}`}
                          >
                            <td className="px-4 py-3 font-medium text-amber-50">
                              {product.name}
                            </td>
                            <td className="px-4 py-3 font-mono text-xs text-stone-400">
                              {product.sku}
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
                              <button
                                type="button"
                                disabled={togglingId === product.id}
                                onClick={() => void handleToggleActive(product)}
                                className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide transition disabled:opacity-50 ${
                                  product.is_active
                                    ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/40 hover:bg-emerald-500/25"
                                    : "bg-stone-500/15 text-stone-400 ring-1 ring-stone-500/40 hover:bg-stone-500/25"
                                }`}
                              >
                                {product.is_active ? "Active" : "Discontinued"}
                              </button>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex flex-wrap gap-2">
                                <Link
                                  href={`/inventory/orders/inbound?productId=${product.id}&locationId=${locationId}`}
                                  className="rounded-full border border-emerald-400/50 px-3 py-1 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-500/10"
                                >
                                  Log inbound
                                </Link>
                                <Link
                                  href={`/inventory/orders/outbound?productId=${product.id}&locationId=${locationId}`}
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
              ))}
            </div>
          )}
        </div>
      </section>

      <AddProductModal
          open={addModalOpen}
          onClose={() => setAddModalOpen(false)}
          onCreated={onRefresh}
        />
    </>
  );
}
