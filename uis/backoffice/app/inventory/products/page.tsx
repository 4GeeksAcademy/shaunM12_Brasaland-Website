"use client";

import { useCallback, useEffect, useState } from "react";
import InventoryPageShell from "@/components/inventory/InventoryPageShell";
import ProductCatalog from "@/components/inventory/ProductCatalog";
import { useApiState } from "@/hooks/useApiState";
import { fetchProducts } from "@/lib/inventory";
import { track, rememberLastLocationId } from "@/lib/telemetry";
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

  useEffect(() => {
    rememberLastLocationId(locationId);
  }, [locationId]);

  const handleLocationChange = useCallback(
    (nextLocationId: number) => {
      if (nextLocationId !== locationId) {
        track("location_filter_applied", {
          location_id: nextLocationId,
          previous_location_id: locationId,
          page_path: "/inventory/products",
        });
      }
      setLocationId(nextLocationId);
    },
    [locationId],
  );

  useEffect(() => {
    if (loading || error) {
      return;
    }
    track("ingredient_list_viewed", {
      location_id: locationId,
      product_count: products.length,
      view_source: "backoffice",
    });
  }, [error, loading, locationId, products.length]);

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
        onLocationChange={handleLocationChange}
        onIncludeInactiveChange={setIncludeInactive}
        onRetry={loadProducts}
        onRefresh={loadProducts}
      />
    </InventoryPageShell>
  );
}
