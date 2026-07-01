import { OrderHistoryRow, OrdersList, Product } from "@/types/inventory";

export function buildOrderHistoryRows(
  orders: OrdersList,
  products: Product[],
): OrderHistoryRow[] {
  const unitBySku = new Map(products.map((product) => [product.sku, product.unit]));

  const inboundRows: OrderHistoryRow[] = orders.inbound.map((order) => ({
    id: order.id,
    kind: "inbound",
    ingredient_name: order.ingredient_name,
    ingredient_sku: order.ingredient_sku,
    quantity: order.quantity,
    unit: unitBySku.get(order.ingredient_sku) ?? null,
    created_at: order.created_at,
    user_uuid: order.user_uuid,
    supplier_name: order.supplier_name,
    location_id: order.location_id,
  }));

  const outboundRows: OrderHistoryRow[] = orders.outbound.map((order) => ({
    id: order.id,
    kind: "outbound",
    ingredient_name: order.ingredient_name,
    ingredient_sku: order.ingredient_sku,
    quantity: order.quantity,
    unit: unitBySku.get(order.ingredient_sku) ?? null,
    created_at: order.created_at,
    user_uuid: order.user_uuid,
    reason: order.reason,
    location_id: order.location_id,
  }));

  return [...inboundRows, ...outboundRows].sort(
    (left, right) =>
      new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}
