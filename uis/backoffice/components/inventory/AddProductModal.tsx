"use client";

import { FormEvent, useState } from "react";
import {
  CATEGORY_LABELS,
  INPUT_CLASS,
  LABEL_CLASS,
} from "@/lib/inventory-constants";
import { createProduct } from "@/lib/inventory";
import { ProductCategory } from "@/types/inventory";

const UNIT_OPTIONS = ["kg", "litre", "unit"] as const;

const CATEGORY_OPTIONS: ProductCategory[] = [
  "meat",
  "seafood",
  "produce",
  "sauce",
  "beverage",
  "packaging",
  "cleaning",
];

interface AddProductModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

const EMPTY_FORM = {
  name: "",
  sku: "",
  unit: "kg",
  category: "meat" as ProductCategory,
};

export default function AddProductModal({
  open,
  onClose,
  onCreated,
}: AddProductModalProps): React.JSX.Element | null {
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) {
    return null;
  }

  const handleClose = (): void => {
    if (submitting) {
      return;
    }
    setForm(EMPTY_FORM);
    setError(null);
    onClose();
  };

  const handleSubmit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createProduct({
        name: form.name.trim(),
        sku: form.sku.trim(),
        unit: form.unit,
        category: form.category,
      });
      setForm(EMPTY_FORM);
      onCreated();
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not create product.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/70 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-product-title"
    >
      <div className="w-full max-w-lg rounded-2xl border border-amber-200/20 bg-stone-900 p-6 shadow-2xl">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 id="add-product-title" className="text-lg font-semibold text-amber-50">
              Add product
            </h2>
            <p className="mt-1 text-sm text-stone-400">
              Adds a new item to the chain-wide Brasaland catalogue (all 14 restaurants).
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="rounded-lg px-2 py-1 text-stone-400 transition hover:bg-stone-800 hover:text-stone-200"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className={LABEL_CLASS}>Product name</span>
            <input
              required
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              className={INPUT_CLASS}
              placeholder="e.g. Beef brisket"
            />
          </label>

          <label className="block">
            <span className={LABEL_CLASS}>SKU</span>
            <input
              required
              value={form.sku}
              onChange={(event) => setForm((current) => ({ ...current, sku: event.target.value }))}
              className={`${INPUT_CLASS} font-mono`}
              placeholder="e.g. BRS-BEEF-099"
            />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className={LABEL_CLASS}>Unit</span>
              <select
                value={form.unit}
                onChange={(event) =>
                  setForm((current) => ({ ...current, unit: event.target.value }))
                }
                className={INPUT_CLASS}
              >
                {UNIT_OPTIONS.map((unit) => (
                  <option key={unit} value={unit}>
                    {unit}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className={LABEL_CLASS}>Category</span>
              <select
                value={form.category}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    category: event.target.value as ProductCategory,
                  }))
                }
                className={INPUT_CLASS}
              >
                {CATEGORY_OPTIONS.map((category) => (
                  <option key={category} value={category}>
                    {CATEGORY_LABELS[category]}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {error ? (
            <p className="rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </p>
          ) : null}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={submitting}
              className="rounded-full border border-stone-600 px-4 py-2 text-sm font-semibold text-stone-300 transition hover:bg-stone-800 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-full bg-amber-500 px-4 py-2 text-sm font-semibold text-stone-950 transition hover:bg-amber-400 disabled:opacity-50"
            >
              {submitting ? "Saving…" : "Create product"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
