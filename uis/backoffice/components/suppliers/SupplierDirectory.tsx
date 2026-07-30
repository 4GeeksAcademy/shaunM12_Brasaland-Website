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
          ? "bo-badge-healthy rounded-full px-2 py-0.5 text-xs font-semibold"
          : "bg-[color:var(--bo-error-bg)] text-[color:var(--bo-error-fg)] ring-1 ring-[color:var(--bo-error-border)]"
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
      <section className="grid gap-4 bo-card-lg md:grid-cols-2">
        <label className="text-sm text-[color:var(--bo-fg)]">
          Filter by country
          <select
            value={countryFilter}
            onChange={(event) => onCountryFilterChange(event.target.value)}
            className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
          >
            <option value="">All countries</option>
            {COUNTRY_OPTIONS.map((country) => (
              <option key={country} value={country}>
                {country}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm text-[color:var(--bo-fg)]">
          Filter by category
          <select
            value={categoryFilter}
            onChange={(event) => onCategoryFilterChange(event.target.value)}
            className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)] outline-none transition focus:border-[color:var(--bo-focus-border)] focus:ring-4 focus:ring-[color:var(--bo-focus-ring)]"
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

      <section className="bo-card-lg">
        <h2 className="bo-subtitle">Register supplier</h2>
        <form className="mt-4 grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
          <label className="text-sm text-[color:var(--bo-fg)] md:col-span-2">
            Name
            <input
              required
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)]"
            />
          </label>

          <label className="text-sm text-[color:var(--bo-fg)]">
            Country
            <select
              value={form.country}
              onChange={(event) => handleCountryChange(event.target.value as SupplierCountry)}
              className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)]"
            >
              {COUNTRY_OPTIONS.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm text-[color:var(--bo-fg)]">
            Status
            <select
              value={form.status}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  status: event.target.value as SupplierStatus,
                }))
              }
              className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)]"
            >
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
            </select>
          </label>

          <label className="text-sm text-[color:var(--bo-fg)]">
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
              className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)]"
            />
          </label>

          <label className="text-sm text-[color:var(--bo-fg)]">
            Contact email
            <input
              type="email"
              value={form.contact_email ?? ""}
              onChange={(event) =>
                setForm((current) => ({ ...current, contact_email: event.target.value }))
              }
              className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)]"
            />
          </label>

          <fieldset className="md:col-span-2">
            <legend className="text-sm text-[color:var(--bo-fg)]">Categories</legend>
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
                        ? "bg-[color:var(--bo-accent)] text-[color:var(--bo-accent-fg)]"
                        : "border border-[color:var(--bo-input-border)] bo-muted hover:border-[color:var(--bo-accent-border)]"
                    }`}
                  >
                    {CATEGORY_LABELS[category]}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <label className="text-sm text-[color:var(--bo-fg)] md:col-span-2">
            Notes
            <textarea
              value={form.notes ?? ""}
              onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
              rows={2}
              className="mt-1 w-full rounded-xl border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-3 py-2 text-[color:var(--bo-fg)]"
            />
          </label>

          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={submitting || form.categories.length === 0}
              className="bo-btn-primary px-5 py-2 text-sm normal-case tracking-normal disabled:cursor-not-allowed"
            >
              {submitting ? "Saving..." : "Register supplier"}
            </button>
          </div>
        </form>
        {formError ? <p className="mt-3 text-sm text-[color:var(--bo-error-fg)]">{formError}</p> : null}
      </section>

      {error ? (
        <ErrorState
          message={error}
          onRetry={onRetry}
          showHomeLink={false}
        />
      ) : null}

      <section className="overflow-hidden rounded-xl border border-[color:var(--bo-card-border)] bg-[color:var(--bo-card)]">
        <div className="border-b border-[color:var(--bo-input-border)] px-4 py-3 text-sm bo-muted">
          {visibleCountLabel}
        </div>
        <div className="overflow-x-auto">
          <table className="bo-table">
            <thead className="bg-[color:var(--bo-panel)] text-xs uppercase tracking-wide text-[color:var(--bo-accent-muted)]/80">
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
                  <tr key={supplier.id} className="border-t border-[color:var(--bo-row-border)]">
                    <td className="px-4 py-3 font-medium text-[color:var(--bo-fg)]">
                      <Link
                        href={`/suppliers/${supplier.id}`}
                        className="text-[color:var(--bo-accent-muted)] underline decoration-[color:var(--bo-accent-border)] underline-offset-2 transition hover:text-[color:var(--bo-heading)]"
                      >
                        {supplier.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 bo-muted">{supplier.country}</td>
                    <td className="px-4 py-3 bo-muted">
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
                          className="w-28 rounded-lg border border-[color:var(--bo-input-border)] bg-[color:var(--bo-input-bg)] px-2 py-1 text-[color:var(--bo-fg)]"
                        />
                        <span className="text-xs bo-muted">
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
                          className="rounded-full border border-[color:var(--bo-accent-border)] px-3 py-1 text-xs font-semibold text-[color:var(--bo-accent-muted)] transition hover:bg-[color:var(--bo-accent-soft)] disabled:opacity-50"
                        >
                          Update rate
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void handleStatusToggle(supplier)}
                          className="bo-btn-secondary px-3 py-1 text-xs normal-case tracking-normal disabled:opacity-50"
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
                  <td colSpan={6} className="px-4 py-8 text-center bo-muted">
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
