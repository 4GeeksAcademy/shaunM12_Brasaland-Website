"use client";

import { useCallback, useEffect, useState } from "react";
import InventoryPageShell from "@/components/inventory/InventoryPageShell";
import ProductCatalog from "@/components/inventory/ProductCatalog";
import { useApiState } from "@/hooks/useApiState";
import { fetchProducts } from "@/lib/inventory";
import { Product } from "@/types/inventory";

export default function InventoryProductsPage(): React.JSX.Element {
  const [locationId, setLocationId] = useState(1);
  const [includeInactive, setIncludeInactive] = useState(false);
  const { data, state, error, execute } = useApiState<Product[]>([]);
  const products = data ?? [];
  const loading = state === "idle" || state === "loading";

  const loadProducts = useCallback(async () => {
    try {
      await execute(() =>
        fetchProducts({ locationId, includeInactive }),
      );
    } catch {
      // useApiState captures the error for ProductCatalog.
    }
  }, [execute, includeInactive, locationId]);

  useEffect(() => {
    void loadProducts();
  }, [loadProducts]);

  return (
    <InventoryPageShell
      eyebrow="Brasaland Inventory"
      title="Ingredient stock"
      description="Chain-wide ingredient catalogue with per-restaurant stock. Every Brasaland location carries the same menu items."
    >
      <ProductCatalog
        products={products}
        loading={loading}
        error={error || null}
        locationId={locationId}
        includeInactive={includeInactive}
        onLocationChange={setLocationId}
        onIncludeInactiveChange={setIncludeInactive}
        onRetry={loadProducts}
        onRefresh={loadProducts}
      />
    </InventoryPageShell>
  );
}
