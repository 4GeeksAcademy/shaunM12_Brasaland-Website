"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import SupplierDeletePanel from "@/components/suppliers/SupplierDeletePanel";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import {
  CATEGORY_LABELS,
  STATUS_LABELS,
  formatCategoryList,
  formatSupplierRate,
} from "@/lib/supplier-constants";
import {
  deleteSupplier,
  fetchSupplierById,
  updateSupplierNotes,
  updateSupplierRate,
  updateSupplierStatus,
} from "@/lib/suppliers-api";
import { Supplier } from "@/types/suppliers";

function StatusBadge({ status }: { status: Supplier["status"] }): React.JSX.Element {
  const isActive = status === "active";
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${
        isActive
          ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/40"
          : "bg-rose-500/15 text-rose-300 ring-1 ring-rose-400/40"
      }`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

export default function SupplierDetailPage(): React.JSX.Element {
  const params = useParams<{ id: string }>();
  const supplierId = Number(params.id);
  const router = useRouter();

  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [rateDraft, setRateDraft] = useState("");
  const [notesDraft, setNotesDraft] = useState("");
  const [notesError, setNotesError] = useState<string | null>(null);
  const [notesSaved, setNotesSaved] = useState(false);

  const loadSupplier = useCallback(async () => {
    if (!Number.isFinite(supplierId) || supplierId <= 0) {
      setError("Invalid supplier id");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const row = await fetchSupplierById(supplierId);
      setSupplier(row);
      setRateDraft(String(row.rate_per_unit));
      setNotesDraft(row.notes ?? "");
    } catch (caught) {
      setSupplier(null);
      setError(caught instanceof Error ? caught.message : "Failed to load supplier");
    } finally {
      setLoading(false);
    }
  }, [supplierId]);

  useEffect(() => {
    void loadSupplier();
  }, [loadSupplier]);

  const handleRateSave = async (): Promise<void> => {
    if (!supplier) {
      return;
    }

    const parsed = Number(rateDraft);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return;
    }

    setBusy(true);
    try {
      const updated = await updateSupplierRate(supplier.id, parsed);
      setSupplier(updated);
      setRateDraft(String(updated.rate_per_unit));
    } finally {
      setBusy(false);
    }
  };

  const handleStatusToggle = async (): Promise<void> => {
    if (!supplier) {
      return;
    }

    setBusy(true);
    try {
      const nextStatus = supplier.status === "active" ? "suspended" : "active";
      const updated = await updateSupplierStatus(supplier.id, nextStatus);
      setSupplier(updated);
    } finally {
      setBusy(false);
    }
  };

  const handleNotesSave = async (): Promise<void> => {
    if (!supplier) {
      return;
    }

    setBusy(true);
    setNotesError(null);
    setNotesSaved(false);
    try {
      const trimmed = notesDraft.trim();
      const updated = await updateSupplierNotes(supplier.id, trimmed || null);
      setSupplier(updated);
      setNotesDraft(updated.notes ?? "");
      setNotesSaved(true);
    } catch (caught) {
      setNotesError(caught instanceof Error ? caught.message : "Could not save notes");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (!supplier) {
      return;
    }

    setBusy(true);
    try {
      await deleteSupplier(supplier.id);
      router.push("/suppliers");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-8 text-stone-100 md:px-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20">
          <Link
            href="/suppliers"
            className="text-sm font-semibold text-amber-300 transition hover:text-amber-200"
          >
            ← Back to directory
          </Link>
        </header>

        {loading ? <LoadingState label="Loading supplier..." /> : null}

        {error ? (
          <ErrorState
            message={error}
            onRetry={() => void loadSupplier()}
            homeHref="/suppliers"
          />
        ) : null}

        {supplier ? (
          <>
            <section className="rounded-xl border border-amber-200/20 bg-stone-900/85 p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h1 className="text-2xl font-extrabold text-amber-100">{supplier.name}</h1>
                  <p className="mt-1 text-sm text-stone-400">Supplier ID {supplier.id}</p>
                </div>
                <StatusBadge status={supplier.status} />
              </div>

              <dl className="mt-6 grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-stone-400">Country</dt>
                  <dd className="mt-1 text-stone-100">{supplier.country}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-stone-400">Contact email</dt>
                  <dd className="mt-1 text-stone-100">
                    {supplier.contact_email ? (
                      <a
                        href={`mailto:${supplier.contact_email}`}
                        className="text-amber-200 underline decoration-amber-300/40 underline-offset-2"
                      >
                        {supplier.contact_email}
                      </a>
                    ) : (
                      <span className="text-stone-500">Not provided</span>
                    )}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs uppercase tracking-wide text-stone-400">Categories</dt>
                  <dd className="mt-2 flex flex-wrap gap-2">
                    {supplier.categories.map((category) => (
                      <span
                        key={category}
                        className="rounded-full bg-amber-300/15 px-3 py-1 text-xs font-semibold text-amber-200 ring-1 ring-amber-300/30"
                      >
                        {CATEGORY_LABELS[category]}
                      </span>
                    ))}
                  </dd>
                  <p className="mt-2 text-sm text-stone-400">
                    {formatCategoryList(supplier.categories)}
                  </p>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-stone-400">Rate updated</dt>
                  <dd className="mt-1 text-stone-100">
                    {new Date(supplier.rate_updated_at).toLocaleString()}
                  </dd>
                </div>
              </dl>
            </section>

            <section className="rounded-xl border border-amber-200/20 bg-stone-900/85 p-6">
              <h2 className="text-lg font-bold text-amber-100">Rate & status</h2>
              <div className="mt-4 flex flex-wrap items-end gap-3">
                <label className="text-sm text-stone-100">
                  Rate per unit ({supplier.currency})
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={rateDraft}
                    onChange={(event) => setRateDraft(event.target.value)}
                    disabled={busy}
                    className="mt-1 block w-40 rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100"
                  />
                </label>
                <p className="pb-2 text-sm text-stone-400">
                  Current: {formatSupplierRate(supplier.rate_per_unit, supplier.currency)}
                </p>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void handleRateSave()}
                  className="rounded-full border border-amber-300/60 px-4 py-2 text-sm font-semibold text-amber-200 transition hover:bg-amber-300/10 disabled:opacity-50"
                >
                  Update rate
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void handleStatusToggle()}
                  className="rounded-full border border-stone-500 px-4 py-2 text-sm font-semibold text-stone-200 transition hover:bg-stone-800 disabled:opacity-50"
                >
                  {supplier.status === "active" ? "Suspend supplier" : "Activate supplier"}
                </button>
              </div>
            </section>

            <section className="rounded-xl border border-amber-200/20 bg-stone-900/85 p-6">
              <h2 className="text-lg font-bold text-amber-100">Notes</h2>
              <p className="mt-1 text-sm text-stone-400">
                Procurement notes for this supplier (delivery schedules, renegotiation history,
                etc.).
              </p>
              <textarea
                value={notesDraft}
                onChange={(event) => {
                  setNotesDraft(event.target.value);
                  setNotesSaved(false);
                }}
                rows={5}
                disabled={busy}
                placeholder="No notes yet. Add context for the procurement team."
                className="mt-4 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100 placeholder:text-stone-500"
              />
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void handleNotesSave()}
                  className="rounded-full bg-amber-300 px-4 py-2 text-sm font-semibold text-stone-950 transition hover:bg-amber-200 disabled:opacity-50"
                >
                  {busy ? "Saving..." : "Save notes"}
                </button>
                {notesSaved ? (
                  <span className="text-sm text-emerald-300">Notes saved.</span>
                ) : null}
              </div>
              {notesError ? <p className="mt-2 text-sm text-rose-300">{notesError}</p> : null}
            </section>

            <SupplierDeletePanel supplier={supplier} busy={busy} onDelete={handleDelete} />
          </>
        ) : null}
      </div>
    </main>
  );
}
