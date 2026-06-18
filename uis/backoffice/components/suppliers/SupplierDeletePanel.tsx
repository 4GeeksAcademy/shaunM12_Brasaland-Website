"use client";

import { useState } from "react";
import { Supplier } from "@/types/suppliers";

interface SupplierDeletePanelProps {
  supplier: Supplier;
  busy: boolean;
  onDelete: () => Promise<void>;
}

export default function SupplierDeletePanel({
  supplier,
  busy,
  onDelete,
}: SupplierDeletePanelProps): React.JSX.Element {
  const [deleteStep, setDeleteStep] = useState<1 | 2 | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const cancelDeleteFlow = (): void => {
    setDeleteStep(null);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async (): Promise<void> => {
    setDeleteError(null);
    try {
      await onDelete();
      cancelDeleteFlow();
    } catch (caught) {
      setDeleteError(
        caught instanceof Error ? caught.message : "Could not delete supplier",
      );
    }
  };

  return (
    <section className="space-y-3 rounded-xl border border-red-300/30 bg-red-300/10 p-4">
      <h2 className="text-xl font-extrabold text-red-300">Danger zone</h2>
      <p className="text-sm text-red-100/90">
        For normal operations, prefer <strong>Suspend</strong>. Removal is for erroneous records
        only.
      </p>

      {deleteStep === null ? (
        <button
          type="button"
          className="rounded-full border border-rose-500/60 bg-rose-950/40 px-4 py-2 text-sm font-semibold text-rose-200 transition hover:bg-rose-500/10 disabled:opacity-50"
          onClick={() => setDeleteStep(1)}
          disabled={busy}
        >
          Remove supplier
        </button>
      ) : (
        <div
          className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4"
          role="alertdialog"
          aria-labelledby="supplier-delete-title"
          aria-describedby="supplier-delete-description"
        >
          <h3 id="supplier-delete-title" className="text-lg font-bold text-rose-200">
            {deleteStep === 1 ? "Remove supplier?" : "Final confirmation"}
          </h3>
          <p id="supplier-delete-description" className="mt-2 text-sm text-rose-100/90">
            {deleteStep === 1 ? (
              <>
                You are about to remove <strong>{supplier.name}</strong> from the directory.
              </>
            ) : (
              <>
                This permanently deletes <strong>{supplier.name}</strong> ({supplier.country}).
                This action cannot be undone.
              </>
            )}
          </p>

          {deleteError ? (
            <p className="mt-3 rounded-md bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {deleteError}
            </p>
          ) : null}

          <div className="mt-4 flex flex-wrap gap-2">
            {deleteStep === 1 ? (
              <>
                <button
                  type="button"
                  onClick={() => setDeleteStep(2)}
                  disabled={busy}
                  className="rounded-full bg-rose-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-600 disabled:opacity-50"
                >
                  Continue to delete
                </button>
                <button
                  type="button"
                  onClick={cancelDeleteFlow}
                  disabled={busy}
                  className="rounded-full border border-stone-500 px-4 py-2 text-sm font-semibold text-stone-200 transition hover:bg-stone-800 disabled:opacity-50"
                >
                  Cancel
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => void handleDeleteConfirm()}
                  disabled={busy}
                  className="rounded-full bg-rose-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-600 disabled:opacity-50"
                >
                  {busy ? "Deleting..." : "Yes, delete permanently"}
                </button>
                <button
                  type="button"
                  onClick={() => setDeleteStep(1)}
                  disabled={busy}
                  className="rounded-full border border-stone-500 px-4 py-2 text-sm font-semibold text-stone-200 transition hover:bg-stone-800 disabled:opacity-50"
                >
                  Go back
                </button>
                <button
                  type="button"
                  onClick={cancelDeleteFlow}
                  disabled={busy}
                  className="rounded-full border border-stone-500 px-4 py-2 text-sm font-semibold text-stone-200 transition hover:bg-stone-800 disabled:opacity-50"
                >
                  Cancel
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
