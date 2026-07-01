import { formatApiError } from "@/lib/api-error";
import { authorizedFetch } from "@/lib/http";
import {
  InboundOrder,
  InboundOrderCreateInput,
  OrdersList,
  OutboundOrder,
  OutboundOrderCreateInput,
  Product,
  ProductCreateInput,
} from "@/types/inventory";

export interface FetchProductsOptions {
  locationId?: number;
  includeInactive?: boolean;
}

function getBaseUrl(): string {
  const configured =
    process.env.NEXT_PUBLIC_INVENTORY_API_BASE_URL?.trim() ??
    process.env.NEXT_PUBLIC_SUPPLIERS_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}

/** Same-origin calls use `/api/inventory/*` (Next proxy) to avoid clashing with UI routes under `/inventory/*`. */
function inventoryPath(suffix: string): string {
  const prefix = getBaseUrl() ? "/inventory" : "/api/inventory";
  return `${prefix}${suffix}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await authorizedFetch(`${getBaseUrl()}${path}`, init);
  } catch (caught) {
    if (caught instanceof Error && caught.message.toLowerCase().includes("session")) {
      throw caught;
    }
    throw new Error(
      "Cannot reach the inventory API. Start it with: npm run api:dev",
    );
  }

  const body = await response.text();
  if (!response.ok) {
    throw new Error(formatApiError(response.status, body));
  }

  if (!body) {
    return undefined as T;
  }

  return JSON.parse(body) as T;
}

export async function fetchProducts(
  options?: FetchProductsOptions,
): Promise<Product[]> {
  const params = new URLSearchParams();
  if (options?.locationId != null) {
    params.set("location_id", String(options.locationId));
  }
  if (options?.includeInactive) {
    params.set("include_inactive", "true");
  }
  const query = params.toString();
  return request<Product[]>(
    inventoryPath(`/products${query ? `?${query}` : ""}`),
  );
}

export async function createProduct(
  payload: ProductCreateInput,
): Promise<Product> {
  return request<Product>(inventoryPath("/products"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateProductActive(
  productId: number,
  isActive: boolean,
  locationId?: number,
): Promise<Product> {
  const params = new URLSearchParams();
  if (locationId != null) {
    params.set("location_id", String(locationId));
  }
  const query = params.toString();
  return request<Product>(
    inventoryPath(`/products/${productId}${query ? `?${query}` : ""}`),
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: isActive }),
    },
  );
}

export async function fetchOrders(): Promise<OrdersList> {
  return request<OrdersList>(inventoryPath("/orders"));
}

export async function createInboundOrder(
  payload: InboundOrderCreateInput,
): Promise<InboundOrder> {
  return request<InboundOrder>(inventoryPath("/orders/inbound"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function createOutboundOrder(
  payload: OutboundOrderCreateInput,
): Promise<OutboundOrder> {
  return request<OutboundOrder>(inventoryPath("/orders/outbound"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
