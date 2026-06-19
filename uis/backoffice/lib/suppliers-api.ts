import {
  Supplier,
  SupplierCreateInput,
  SupplierStatus,
} from "@/types/suppliers";
import { formatApiError } from "@/lib/api-error";
import { authorizedFetch } from "@/lib/http";

function getBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_SUPPLIERS_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await authorizedFetch(`${getBaseUrl()}${path}`, init);
  } catch (caught) {
    // authorizedFetch throws (after redirecting) when the session is gone.
    if (caught instanceof Error && caught.message.toLowerCase().includes("session")) {
      throw caught;
    }
    throw new Error(
      "Cannot reach the supplier directory API. Start it with: npm run api:dev",
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const body = await response.text();
  if (!response.ok) {
    throw new Error(formatApiError(response.status, body));
  }

  return JSON.parse(body) as T;
}

export async function fetchSuppliers(filters?: {
  country?: string;
  category?: string;
}): Promise<Supplier[]> {
  const params = new URLSearchParams();
  if (filters?.country) {
    params.set("country", filters.country);
  }
  if (filters?.category) {
    params.set("category", filters.category);
  }
  const query = params.toString();
  return request<Supplier[]>(`/api/suppliers${query ? `?${query}` : ""}`);
}

export async function fetchSupplierById(supplierId: number): Promise<Supplier> {
  return request<Supplier>(`/api/suppliers/${supplierId}`);
}

export async function createSupplier(payload: SupplierCreateInput): Promise<Supplier> {
  const body = {
    ...payload,
    contact_email: payload.contact_email?.trim() || null,
    notes: payload.notes?.trim() || null,
  };

  return request<Supplier>("/api/suppliers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function updateSupplierRate(
  supplierId: number,
  rate_per_unit: number,
): Promise<Supplier> {
  return request<Supplier>(`/api/suppliers/${supplierId}/rate`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rate_per_unit }),
  });
}

export async function updateSupplierStatus(
  supplierId: number,
  status: SupplierStatus,
): Promise<Supplier> {
  return request<Supplier>(`/api/suppliers/${supplierId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

export async function updateSupplierNotes(
  supplierId: number,
  notes: string | null,
): Promise<Supplier> {
  return request<Supplier>(`/api/suppliers/${supplierId}/notes`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes }),
  });
}

export async function deleteSupplier(supplierId: number): Promise<void> {
  await request<void>(`/api/suppliers/${supplierId}`, {
    method: "DELETE",
  });
}
