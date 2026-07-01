"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  INPUT_CLASS,
  LABEL_CLASS,
  RESTAURANT_LOCATIONS,
  formatLocationLabel,
  getQuantityConstraints,
  getSupplierForLocation,
  isValidQuantity,
} from "@/lib/inventory-constants";
import { createInboundOrder } from "@/lib/inventory";
import { Product } from "@/types/inventory";

interface InboundOrderFormProps {
  products: Product[];
  productsLoading: boolean;
}

const EMPTY_FORM = {
  ingredient_id: "",
  quantity: "",
  supplier_name: "",
  location_id: "",
};

function resolveLocationId(preferredLocationId?: string | null): number {
  const preferred = preferredLocationId
    ? RESTAURANT_LOCATIONS.find((location) => String(location.id) === preferredLocationId)
    : undefined;
  return preferred?.id ?? RESTAURANT_LOCATIONS[0]?.id ?? 1;
}

function applyProductDefaults(
  product: Product,
  current: typeof EMPTY_FORM,
  preferredLocationId?: string | null,
): typeof EMPTY_FORM {
  const locationId = resolveLocationId(preferredLocationId);
  return {
    ...current,
    ingredient_id: String(product.id),
    supplier_name: getSupplierForLocation(product.category, locationId),
    location_id: String(locationId),
    quantity: "",
  };
}

export default function InboundOrderForm({
  products,
  productsLoading,
}: InboundOrderFormProps): React.JSX.Element {
  const searchParams = useSearchParams();
  const preselectedId = searchParams.get("productId");
  const preselectedLocationId = searchParams.get("locationId");

  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const selectedProduct = useMemo(
    () => products.find((product) => String(product.id) === form.ingredient_id),
    [form.ingredient_id, products],
  );

  const quantityConstraints = getQuantityConstraints(selectedProduct?.unit);

  useEffect(() => {
    if (!preselectedId || products.length === 0) {
      return;
    }
    const product = products.find((item) => String(item.id) === preselectedId);
    if (product) {
      setForm(applyProductDefaults(product, EMPTY_FORM, preselectedLocationId));
    }
  }, [preselectedId, preselectedLocationId, products]);

  const handleProductChange = (productId: string): void => {
    const product = products.find((item) => String(item.id) === productId);
    if (!product) {
      setForm((current) => ({ ...current, ingredient_id: productId }));
      return;
    }
    setForm(applyProductDefaults(product, form, form.location_id || preselectedLocationId));
  };

  const handleLocationChange = (locationId: string): void => {
    const numericId = Number(locationId);
    setForm((current) => ({
      ...current,
      location_id: locationId,
      supplier_name: selectedProduct
        ? getSupplierForLocation(selectedProduct.category, numericId)
        : current.supplier_name,
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setFormError(null);
    setSuccessMessage(null);

    const ingredientId = Number(form.ingredient_id);
    const quantity = Number(form.quantity);
    const locationId = Number(form.location_id);

    if (!ingredientId || !selectedProduct) {
      setFormError("Select a product.");
      return;
    }

    if (!isValidQuantity(quantity, selectedProduct.unit)) {
      setFormError(
        `Enter a valid quantity in ${selectedProduct.unit} (min ${quantityConstraints.min}, step ${quantityConstraints.step}).`,
      );
      return;
    }

    if (!RESTAURANT_LOCATIONS.some((location) => location.id === locationId)) {
      setFormError("Select a restaurant.");
      return;
    }

    setSubmitting(true);
    try {
      await createInboundOrder({
        ingredient_id: ingredientId,
        quantity,
        supplier_name: form.supplier_name,
        location_id: locationId,
      });
      const resetProduct = preselectedId
        ? products.find((item) => String(item.id) === preselectedId)
        : undefined;
      setForm(
        resetProduct
          ? applyProductDefaults(resetProduct, EMPTY_FORM, preselectedLocationId)
          : EMPTY_FORM,
      );
      setSuccessMessage(
        `Inbound delivery for ${selectedProduct.name} recorded at ${formatLocationLabel(locationId)}.`,
      );
    } catch (caught) {
      setFormError(
        caught instanceof Error ? caught.message : "Could not record inbound order.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="rounded-xl border border-amber-200/20 bg-stone-900/85 p-6">
      <form className="grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
        <label className="md:col-span-2">
          <span className={LABEL_CLASS}>Product</span>
          <select
            required
            disabled={productsLoading || products.length === 0}
            value={form.ingredient_id}
            onChange={(event) => handleProductChange(event.target.value)}
            className={INPUT_CLASS}
          >
            <option value="">Select a product…</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name} ({product.sku})
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className={LABEL_CLASS}>
            Quantity received ({selectedProduct?.unit ?? "unit"})
          </span>
          <input
            required
            type="number"
            min={quantityConstraints.min}
            step={quantityConstraints.step}
            value={form.quantity}
            onChange={(event) =>
              setForm((current) => ({ ...current, quantity: event.target.value }))
            }
            className={INPUT_CLASS}
            placeholder={quantityConstraints.placeholder}
            disabled={!selectedProduct}
          />
        </label>

        <label>
          <span className={LABEL_CLASS}>Receiving restaurant</span>
          <select
            required
            value={form.location_id}
            onChange={(event) => handleLocationChange(event.target.value)}
            className={INPUT_CLASS}
            disabled={!selectedProduct}
          >
            {RESTAURANT_LOCATIONS.map((location) => (
              <option key={location.id} value={location.id}>
                {location.name} — {location.city}
              </option>
            ))}
          </select>
        </label>

        <label className="md:col-span-2">
          <span className={LABEL_CLASS}>Supplier (from restaurant market)</span>
          <input
            required
            readOnly
            type="text"
            value={form.supplier_name}
            className={`${INPUT_CLASS} cursor-not-allowed text-stone-300`}
            placeholder="Select a product and restaurant…"
          />
        </label>

        {formError ? (
          <p role="alert" className="md:col-span-2 text-sm text-rose-300">
            {formError}
          </p>
        ) : null}

        {successMessage ? (
          <p
            role="status"
            className="md:col-span-2 rounded-lg border border-emerald-400/30 bg-emerald-950/40 px-3 py-2 text-sm text-emerald-200"
          >
            {successMessage}
          </p>
        ) : null}

        <div className="md:col-span-2">
          <button
            type="submit"
            disabled={submitting || productsLoading || !selectedProduct}
            className="rounded-full bg-amber-300 px-5 py-2 text-sm font-semibold text-stone-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Saving…" : "Record inbound delivery"}
          </button>
        </div>
      </form>
    </section>
  );
}
