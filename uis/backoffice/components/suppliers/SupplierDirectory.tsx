"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import ErrorState from "@/components/ui/ErrorState";
import {
  CATEGORY_LABELS,
  COUNTRY_OPTIONS,
  EMPTY_SUPPLIER_FORM,
  SUPPLIER_CATEGORIES,
  SupplierCreateInput,
  currencyForCountry,
  formatCategoryList,
  formatSupplierRate,
} from "@/lib/supplier-constants";
import { Supplier, SupplierCategory, SupplierCountry, SupplierStatus } from "@/types/suppliers";

interface SupplierDirectoryProps {
  suppliers: Supplier[];
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
  countryFilter: string;
  categoryFilter: string;
  onCountryFilterChange: (value: string) => void;
  onCategoryFilterChange: (value: string) => void;
  onCreate: (payload: SupplierCreateInput) => Promise<void>;
  onUpdateRate: (supplierId: number, rate: number) => Promise<void>;
  onToggleStatus: (supplier: Supplier) => Promise<void>;
}

function StatusBadge({ status }: { status: SupplierStatus }): React.JSX.Element {
  const isActive = status === "active";
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${
        isActive
          ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/40"
          : "bg-rose-500/15 text-rose-300 ring-1 ring-rose-400/40"
      }`}
    >
      {isActive ? "Active" : "Suspended"}
    </span>
  );
}

export default function SupplierDirectory({
  suppliers,
  loading,
  error,
  onRetry,
  countryFilter,
  categoryFilter,
  onCountryFilterChange,
  onCategoryFilterChange,
  onCreate,
  onUpdateRate,
  onToggleStatus,
}: SupplierDirectoryProps): React.JSX.Element {
  const [form, setForm] = useState<SupplierCreateInput>(EMPTY_SUPPLIER_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [rateDrafts, setRateDrafts] = useState<Record<number, string>>({});
  const [rowBusyId, setRowBusyId] = useState<number | null>(null);

  const visibleCountLabel = useMemo(() => {
    if (loading) {
      return "Loading suppliers...";
    }
    return `${suppliers.length} supplier${suppliers.length === 1 ? "" : "s"} shown`;
  }, [loading, suppliers.length]);

  const toggleCategory = (category: SupplierCategory): void => {
    setForm((current) => {
      const selected = new Set(current.categories);
      if (selected.has(category)) {
        selected.delete(category);
      } else {
        selected.add(category);
      }
      return {
        ...current,
        categories: SUPPLIER_CATEGORIES.filter((item) => selected.has(item)),
      };
    });
  };

  const handleCountryChange = (country: SupplierCountry): void => {
    setForm((current) => ({
      ...current,
      country,
      currency: currencyForCountry(country),
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      await onCreate(form);
      setForm(EMPTY_SUPPLIER_FORM);
    } catch (caught) {
      setFormError(caught instanceof Error ? caught.message : "Could not register supplier");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRateSave = async (supplier: Supplier): Promise<void> => {
    const raw = rateDrafts[supplier.id] ?? String(supplier.rate_per_unit);
    const parsed = Number(raw);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return;
    }

    setRowBusyId(supplier.id);
    try {
      await onUpdateRate(supplier.id, parsed);
      setRateDrafts((current) => {
        const next = { ...current };
        delete next[supplier.id];
        return next;
      });
    } finally {
      setRowBusyId(null);
    }
  };

  const handleStatusToggle = async (supplier: Supplier): Promise<void> => {
    setRowBusyId(supplier.id);
    try {
      await onToggleStatus(supplier);
    } finally {
      setRowBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <section className="grid gap-4 rounded-xl border border-amber-200/20 bg-stone-900/85 p-4 md:grid-cols-2">
        <label className="text-sm text-stone-100">
          Filter by country
          <select
            value={countryFilter}
            onChange={(event) => onCountryFilterChange(event.target.value)}
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
          >
            <option value="">All countries</option>
            {COUNTRY_OPTIONS.map((country) => (
              <option key={country} value={country}>
                {country}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm text-stone-100">
          Filter by category
          <select
            value={categoryFilter}
            onChange={(event) => onCategoryFilterChange(event.target.value)}
            className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 outline-none transition focus:border-amber-300 focus:ring-4 focus:ring-amber-300/20"
          >
            <option value="">All categories</option>
            {SUPPLIER_CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {CATEGORY_LABELS[category]}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="rounded-xl border border-amber-200/20 bg-stone-900/85 p-4">
        <h2 className="text-lg font-bold text-amber-100">Register supplier</h2>
        <form className="mt-4 grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
          <label className="text-sm text-stone-100 md:col-span-2">
            Name
            <input
              required
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100"
            />
          </label>

          <label className="text-sm text-stone-100">
            Country
            <select
              value={form.country}
              onChange={(event) => handleCountryChange(event.target.value as SupplierCountry)}
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100"
            >
              {COUNTRY_OPTIONS.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm text-stone-100">
            Status
            <select
              value={form.status}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  status: event.target.value as SupplierStatus,
                }))
              }
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100"
            >
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
            </select>
          </label>

          <label className="text-sm text-stone-100">
            Rate per unit ({form.currency})
            <input
              required
              type="number"
              min="0.01"
              step="0.01"
              value={form.rate_per_unit || ""}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  rate_per_unit: Number(event.target.value),
                }))
              }
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100"
            />
          </label>

          <label className="text-sm text-stone-100">
            Contact email
            <input
              type="email"
              value={form.contact_email ?? ""}
              onChange={(event) =>
                setForm((current) => ({ ...current, contact_email: event.target.value }))
              }
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100"
            />
          </label>

          <fieldset className="md:col-span-2">
            <legend className="text-sm text-stone-100">Categories</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {SUPPLIER_CATEGORIES.map((category) => {
                const selected = form.categories.includes(category);
                return (
                  <button
                    key={category}
                    type="button"
                    onClick={() => toggleCategory(category)}
                    className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                      selected
                        ? "bg-amber-300 text-stone-950"
                        : "border border-stone-600 text-stone-300 hover:border-amber-300/60"
                    }`}
                  >
                    {CATEGORY_LABELS[category]}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <label className="text-sm text-stone-100 md:col-span-2">
            Notes
            <textarea
              value={form.notes ?? ""}
              onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
              rows={2}
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100"
            />
          </label>

          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={submitting || form.categories.length === 0}
              className="rounded-full bg-amber-300 px-5 py-2 text-sm font-semibold text-stone-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Saving..." : "Register supplier"}
            </button>
          </div>
        </form>
        {formError ? <p className="mt-3 text-sm text-rose-300">{formError}</p> : null}
      </section>

      {error ? (
        <ErrorState
          message={error}
          onRetry={onRetry}
          showHomeLink={false}
        />
      ) : null}

      <section className="overflow-hidden rounded-xl border border-amber-200/20 bg-stone-900/85">
        <div className="border-b border-stone-700 px-4 py-3 text-sm text-stone-300">
          {visibleCountLabel}
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-stone-950/70 text-xs uppercase tracking-wide text-amber-200/80">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Country</th>
                <th className="px-4 py-3">Categories</th>
                <th className="px-4 py-3">Rate</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((supplier) => {
                const busy = rowBusyId === supplier.id;
                return (
                  <tr key={supplier.id} className="border-t border-stone-800/80">
                    <td className="px-4 py-3 font-medium text-stone-100">
                      <Link
                        href={`/suppliers/${supplier.id}`}
                        className="text-amber-200 underline decoration-amber-300/40 underline-offset-2 transition hover:text-amber-100 hover:decoration-amber-200"
                      >
                        {supplier.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-stone-300">{supplier.country}</td>
                    <td className="px-4 py-3 text-stone-300">
                      {formatCategoryList(supplier.categories)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          min="0.01"
                          step="0.01"
                          value={rateDrafts[supplier.id] ?? String(supplier.rate_per_unit)}
                          onChange={(event) =>
                            setRateDrafts((current) => ({
                              ...current,
                              [supplier.id]: event.target.value,
                            }))
                          }
                          className="w-28 rounded-lg border border-stone-600 bg-stone-950/80 px-2 py-1 text-stone-100"
                        />
                        <span className="text-xs text-stone-400">
                          {formatSupplierRate(supplier.rate_per_unit, supplier.currency)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={supplier.status} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void handleRateSave(supplier)}
                          className="rounded-full border border-amber-300/60 px-3 py-1 text-xs font-semibold text-amber-200 transition hover:bg-amber-300/10 disabled:opacity-50"
                        >
                          Update rate
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void handleStatusToggle(supplier)}
                          className="rounded-full border border-stone-500 px-3 py-1 text-xs font-semibold text-stone-200 transition hover:bg-stone-800 disabled:opacity-50"
                        >
                          {supplier.status === "active" ? "Suspend" : "Activate"}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!loading && suppliers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-stone-400">
                    No suppliers match the current filters.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
