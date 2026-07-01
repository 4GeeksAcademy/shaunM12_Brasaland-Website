"use client";

import { useCallback, useEffect } from "react";
import InboundOrderForm from "@/components/inventory/InboundOrderForm";
import InventoryPageShell from "@/components/inventory/InventoryPageShell";
import ErrorState from "@/components/ui/ErrorState";
import { useApiState } from "@/hooks/useApiState";
import { fetchProducts } from "@/lib/inventory";
import { Product } from "@/types/inventory";

export default function InboundOrderPage(): React.JSX.Element {
  const { data, state, error, execute } = useApiState<Product[]>([]);
  const products = data ?? [];
  const loading = state === "idle" || state === "loading";

  const loadProducts = useCallback(async () => {
    try {
      await execute(() => fetchProducts({ includeInactive: true }));
    } catch {
      // surfaced below when products are needed for the selector
    }
  }, [execute]);

  useEffect(() => {
    void loadProducts();
  }, [loadProducts]);

  return (
    <InventoryPageShell
      eyebrow="Brasaland Inventory"
      title="Register inbound delivery"
      description="Log a supplier delivery to increase stock. Select the product by name — never enter a raw ingredient ID."
    >
      {error ? (
        <ErrorState message={error} onRetry={loadProducts} showHomeLink={false} />
      ) : (
        <InboundOrderForm products={products} productsLoading={loading} />
      )}
    </InventoryPageShell>
  );
}
