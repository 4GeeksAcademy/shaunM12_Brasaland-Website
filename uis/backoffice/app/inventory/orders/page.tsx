"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import InventoryPageShell from "@/components/inventory/InventoryPageShell";
import OrdersHistoryTable from "@/components/inventory/OrdersHistoryTable";
import { useApiState } from "@/hooks/useApiState";
import { ALL_RESTAURANTS_LOCATION_ID } from "@/lib/inventory-constants";
import { fetchOrders, fetchProducts } from "@/lib/inventory";
import { buildOrderHistoryRows } from "@/lib/inventory-orders";
import { OrdersList, Product } from "@/types/inventory";

interface OrdersPageData {
  orders: OrdersList;
  products: Product[];
}

export default function OrdersHistoryPage(): React.JSX.Element {
  const [locationId, setLocationId] = useState(ALL_RESTAURANTS_LOCATION_ID);
  const { data, state, error, execute } = useApiState<OrdersPageData | null>(null);
  const loading = state === "idle" || state === "loading";

  const loadOrders = useCallback(async () => {
    try {
      await execute(async () => {
        const [orders, products] = await Promise.all([
          fetchOrders(),
          fetchProducts({ includeInactive: true }),
        ]);
        return { orders, products };
      });
    } catch {
      // useApiState captures the error for OrdersHistoryTable.
    }
  }, [execute]);

  useEffect(() => {
    void loadOrders();
  }, [loadOrders]);

  const rows = useMemo(() => {
    if (!data) {
      return [];
    }
    const allRows = buildOrderHistoryRows(data.orders, data.products);
    if (locationId === ALL_RESTAURANTS_LOCATION_ID) {
      return allRows;
    }
    return allRows.filter((row) => row.location_id === locationId);
  }, [data, locationId]);

  return (
    <InventoryPageShell
      eyebrow="Brasaland Inventory"
      title="Order history"
      description="Read-only log of all inbound deliveries and outbound consumption or waste. Filter by restaurant or view the full chain history."
    >
      <OrdersHistoryTable
        rows={rows}
        loading={loading}
        error={error || null}
        locationId={locationId}
        onLocationChange={setLocationId}
        onRetry={loadOrders}
      />
    </InventoryPageShell>
  );
}
