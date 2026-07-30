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
import { inventoryOrderPrefillHref } from "@/lib/query-params";
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
            <label className="flex cursor-pointer items-center gap-2 text-sm bo-muted">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(event) => onIncludeInactiveChange(event.target.checked)}
                className="rounded border-[color:var(--bo-input-border)] bg-[color:var(--bo-card)] text-[color:var(--bo-heading)] focus:ring-[color:var(--bo-focus-border)]"
              />
              Show discontinued
            </label>
            <button
              type="button"
              onClick={() => setAddModalOpen(true)}
              className="bo-btn-primary px-4 py-2 text-sm normal-case tracking-normal"
            >
              Add product
            </button>
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-[color:var(--bo-card-border)] bg-[color:var(--bo-card)]">
          <div className="border-b border-[color:var(--bo-panel-border)] px-4 py-3 text-xs bo-muted">
            {loading
              ? "Loading products..."
              : selectedLocation
                ? `${products.length} product${products.length === 1 ? "" : "s"} at ${formatLocationLabel(locationId)}`
                : `${products.length} product${products.length === 1 ? "" : "s"}`}
          </div>

          {toggleError ? (
            <p className="border-b border-[color:var(--bo-error-border)] bg-[color:var(--bo-error-bg)] px-4 py-2 text-sm text-[color:var(--bo-error-fg)]">
              {toggleError}
            </p>
          ) : null}

          {loading ? (
            <p className="px-4 py-8 text-sm bo-muted">
              Fetching live stock for this restaurant…
            </p>
          ) : products.length === 0 ? (
            <p className="px-4 py-8 text-sm bo-muted">
              No products for this restaurant
              {includeInactive ? "" : " (try showing discontinued items)"}.
            </p>
          ) : (
            <div className="overflow-x-auto">
              {grouped.map(({ category, items }) => (
                <div key={category}>
                  <div className="bg-[color:var(--bo-input-bg)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.1em] text-[color:var(--bo-accent-muted)]/80">
                    {CATEGORY_LABELS[category] ?? category}
                  </div>
                  <table className="bo-table">
                    <thead className="bg-[color:var(--bo-row-bg)] text-xs uppercase tracking-[0.08em] bo-muted">
                      <tr>
                        <th className="px-4 py-2 font-semibold">Product</th>
                        <th className="px-4 py-2 font-semibold">SKU</th>
                        <th className="px-4 py-2 font-semibold">Stock @ site</th>
                        <th className="px-4 py-2 font-semibold">Stock level</th>
                        <th className="px-4 py-2 font-semibold">Catalog</th>
                        <th className="px-4 py-2 font-semibold">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[color:var(--bo-row-border)]">
                      {items.map((product) => {
                        const level = getStockLevel(
                          product.current_stock,
                          product.min_stock_threshold,
                        );
                        return (
                          <tr
                            key={product.id}
                            className={`bo-fg-secondary ${!product.is_active ? "opacity-70" : ""}`}
                          >
                            <td className="px-4 py-3 font-medium text-[color:var(--bo-heading)]">
                              {product.name}
                            </td>
                            <td className="px-4 py-3 font-mono text-xs bo-muted">
                              {product.sku}
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
                              <button
                                type="button"
                                disabled={togglingId === product.id}
                                onClick={() => void handleToggleActive(product)}
                                className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide transition disabled:opacity-50 ${
                                  product.is_active
                                    ? "bo-badge-healthy hover:opacity-90"
                                    : "bg-[color:var(--bo-row-bg)] bo-muted ring-1 ring-[color:var(--bo-row-border)] hover:opacity-90"
                                }`}
                              >
                                {product.is_active ? "Active" : "Discontinued"}
                              </button>
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
