import {
  ApiValidationError,
  Supplier,
  SupplierCreateInput,
  SupplierStatus,
} from "@/types/suppliers";

function getBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_SUPPLIERS_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}

function formatApiError(status: number, body: string): string {
  try {
    const parsed = JSON.parse(body) as ApiValidationError;
    if (Array.isArray(parsed.detail)) {
      return parsed.detail
        .map((item) => item.msg ?? "Validation error")
        .join("; ");
    }
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
  } catch {
    // keep raw body
  }
  return body || `Request failed (${status})`;
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${getBaseUrl()}${path}`, {
      ...init,
      cache: "no-store",
    });
  } catch {
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
