"use client";

import { useCallback, useEffect, useState } from "react";
import InventoryPageShell from "@/components/inventory/InventoryPageShell";
import OutboundOrderForm from "@/components/inventory/OutboundOrderForm";
import ErrorState from "@/components/ui/ErrorState";
import { useApiState } from "@/hooks/useApiState";
import { fetchProducts } from "@/lib/inventory";
import { Product } from "@/types/inventory";

export default function OutboundOrderPage(): React.JSX.Element {
  const [locationId, setLocationId] = useState(1);
  const { data, state, error, execute } = useApiState<Product[]>([]);
  const products = data ?? [];
  const loading = state === "idle" || state === "loading";

  const loadProducts = useCallback(async () => {
    try {
      await execute(() =>
        fetchProducts({ locationId, includeInactive: true }),
      );
    } catch {
      // surfaced below when products are needed for the selector
    }
  }, [execute, locationId]);

  useEffect(() => {
    void loadProducts();
  }, [loadProducts]);

  return (
    <InventoryPageShell
      eyebrow="Brasaland Inventory"
      title="Register outbound order"
      description="Log consumption or waste. Available stock updates when you change the product or restaurant — the API enforces the limit at the selected site on submit."
    >
      {error ? (
        <ErrorState message={error} onRetry={loadProducts} showHomeLink={false} />
      ) : (
        <OutboundOrderForm
          products={products}
          productsLoading={loading}
          locationId={locationId}
          onLocationChange={setLocationId}
        />
      )}
    </InventoryPageShell>
  );
}
