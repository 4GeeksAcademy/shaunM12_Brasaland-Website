"use client";

import { useCallback, useEffect, useState } from "react";
import SupplierDirectory from "@/components/suppliers/SupplierDirectory";
import { useApiState } from "@/hooks/useApiState";
import { SupplierCreateInput } from "@/lib/supplier-constants";
import {
  createSupplier,
  fetchSuppliers,
  updateSupplierRate,
  updateSupplierStatus,
} from "@/lib/suppliers-api";
import { Supplier } from "@/types/suppliers";

export default function SuppliersPage(): React.JSX.Element {
  const {
    data: suppliersData,
    state,
    error,
    execute,
  } = useApiState<Supplier[]>([]);
  const [countryFilter, setCountryFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const suppliers = suppliersData ?? [];
  // Treat the initial "idle" paint as loading so the table never flashes an
  // empty/"no results" state before the first fetch resolves.
  const loading = state === "idle" || state === "loading";

  const loadSuppliers = useCallback(async () => {
    try {
      await execute(() =>
        fetchSuppliers({
          country: countryFilter || undefined,
          category: categoryFilter || undefined,
        }),
      );
    } catch {
      // Error state is captured by useApiState; surfaced via ErrorState below.
    }
  }, [categoryFilter, countryFilter, execute]);

  useEffect(() => {
    void loadSuppliers();
  }, [loadSuppliers]);

  const handleCreate = async (payload: SupplierCreateInput): Promise<void> => {
    await createSupplier(payload);
    await loadSuppliers();
  };

  const handleUpdateRate = async (supplierId: number, rate: number): Promise<void> => {
    await updateSupplierRate(supplierId, rate);
    await loadSuppliers();
  };

  const handleToggleStatus = async (supplier: Supplier): Promise<void> => {
    const nextStatus = supplier.status === "active" ? "suspended" : "active";
    await updateSupplierStatus(supplier.id, nextStatus);
    await loadSuppliers();
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-8 text-stone-100 md:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20">
          <p className="text-sm uppercase tracking-[0.12em] text-amber-300">
            Brasaland Supplier Directory
          </p>
          <h1 className="mt-2 text-2xl font-extrabold text-amber-100 md:text-3xl">
            Procurement Supplier Directory
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-stone-300">
            Single source of truth for Brasaland suppliers across Colombia and Florida. Filter by
            market and category, register new vendors, update rates, and suspend suppliers when
            needed.
          </p>
        </header>

        <SupplierDirectory
          suppliers={suppliers}
          loading={loading}
          error={error || null}
          onRetry={loadSuppliers}
          countryFilter={countryFilter}
          categoryFilter={categoryFilter}
          onCountryFilterChange={setCountryFilter}
          onCategoryFilterChange={setCategoryFilter}
          onCreate={handleCreate}
          onUpdateRate={handleUpdateRate}
          onToggleStatus={handleToggleStatus}
        />
      </div>
    </main>
  );
}
