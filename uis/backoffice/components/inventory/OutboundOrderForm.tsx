"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  EXIT_REASON_OPTIONS,
  INPUT_CLASS,
  LABEL_CLASS,
  RESTAURANT_LOCATIONS,
  formatLocationLabel,
  getQuantityConstraints,
  isValidQuantity,
} from "@/lib/inventory-constants";
import { createOutboundOrder } from "@/lib/inventory";
import { ExitReason, Product } from "@/types/inventory";

interface OutboundOrderFormProps {
  products: Product[];
  productsLoading: boolean;
  locationId: number;
  onLocationChange: (locationId: number) => void;
}

const EMPTY_FORM = {
  ingredient_id: "",
  quantity: "",
  reason: "consumption" as ExitReason,
};

function resolveLocationId(preferredLocationId?: string | null): number {
  const preferred = preferredLocationId
    ? RESTAURANT_LOCATIONS.find((location) => String(location.id) === preferredLocationId)
    : undefined;
  return preferred?.id ?? RESTAURANT_LOCATIONS[0]?.id ?? 1;
}

export default function OutboundOrderForm({
  products,
  productsLoading,
  locationId,
  onLocationChange,
}: OutboundOrderFormProps): React.JSX.Element {
  const searchParams = useSearchParams();
  const preselectedId = searchParams.get("productId");
  const preselectedLocationId = searchParams.get("locationId");

  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [quantityError, setQuantityError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const selectedProduct = useMemo(
    () => products.find((product) => String(product.id) === form.ingredient_id),
    [form.ingredient_id, products],
  );

  const quantityConstraints = getQuantityConstraints(selectedProduct?.unit);
  const parsedQuantity = Number(form.quantity);
  const exceedsStock =
    selectedProduct !== undefined &&
    Number.isFinite(parsedQuantity) &&
    parsedQuantity > 0 &&
    parsedQuantity > selectedProduct.current_stock;

  useEffect(() => {
    if (!preselectedLocationId) {
      return;
    }
    onLocationChange(resolveLocationId(preselectedLocationId));
  }, [preselectedLocationId, onLocationChange]);

  useEffect(() => {
    if (!preselectedId || products.length === 0) {
      return;
    }
    const product = products.find((item) => String(item.id) === preselectedId);
    if (product) {
      setForm((current) => ({
        ...current,
        ingredient_id: String(product.id),
        quantity: "",
      }));
    }
  }, [preselectedId, products]);

  const handleProductChange = (productId: string): void => {
    setQuantityError(null);
    setForm((current) => ({
      ...current,
      ingredient_id: productId,
      quantity: "",
    }));
  };

  const handleLocationChange = (nextLocationId: number): void => {
    setQuantityError(null);
    onLocationChange(nextLocationId);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setFormError(null);
    setQuantityError(null);
    setSuccessMessage(null);

    const ingredientId = Number(form.ingredient_id);
    const quantity = Number(form.quantity);

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
      await createOutboundOrder({
        ingredient_id: ingredientId,
        quantity,
        reason: form.reason,
        location_id: locationId,
      });
      if (preselectedId) {
        setForm({
          ingredient_id: preselectedId,
          quantity: "",
          reason: "consumption",
        });
      } else {
        setForm(EMPTY_FORM);
      }
      setSuccessMessage(
        `Outbound order for ${selectedProduct.name} recorded at ${formatLocationLabel(locationId)}.`,
      );
    } catch (caught) {
      const message =
        caught instanceof Error ? caught.message : "Could not record outbound order.";
      if (message.toLowerCase().includes("insufficient stock")) {
        setQuantityError(message);
      } else {
        setFormError(message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="rounded-xl border border-amber-200/20 bg-stone-900/85 p-6">
      <form className="grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
        <label className="md:col-span-2">
          <span className={LABEL_CLASS}>Restaurant</span>
          <select
            required
            value={locationId}
            onChange={(event) => handleLocationChange(Number(event.target.value))}
            className={INPUT_CLASS}
          >
            {RESTAURANT_LOCATIONS.map((location) => (
              <option key={location.id} value={location.id}>
                {location.name} — {location.city}
              </option>
            ))}
          </select>
        </label>

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

        {selectedProduct ? (
          <p className="md:col-span-2 rounded-lg border border-amber-300/20 bg-amber-950/20 px-3 py-2 text-sm text-amber-100">
            Available stock at {formatLocationLabel(locationId)}:{" "}
            <span className="font-semibold">
              {productsLoading ? "…" : `${selectedProduct.current_stock} ${selectedProduct.unit}`}
            </span>
          </p>
        ) : null}

        <label>
          <span className={LABEL_CLASS}>
            Quantity used ({selectedProduct?.unit ?? "unit"})
          </span>
          <input
            required
            type="number"
            min={quantityConstraints.min}
            step={quantityConstraints.step}
            value={form.quantity}
            onChange={(event) => {
              setQuantityError(null);
              setForm((current) => ({ ...current, quantity: event.target.value }));
            }}
            className={INPUT_CLASS}
            placeholder={quantityConstraints.placeholder}
            disabled={!selectedProduct || productsLoading}
          />
          {exceedsStock ? (
            <p className="mt-2 text-xs text-amber-300">
              Warning: quantity exceeds available stock at this restaurant.
            </p>
          ) : null}
          {quantityError ? (
            <p role="alert" className="mt-2 text-xs text-rose-300">
              {quantityError}
            </p>
          ) : null}
        </label>

        <label>
          <span className={LABEL_CLASS}>Reason</span>
          <select
            required
            value={form.reason}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                reason: event.target.value as ExitReason,
              }))
            }
            className={INPUT_CLASS}
          >
            {EXIT_REASON_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
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
            {submitting ? "Saving…" : "Record outbound order"}
          </button>
        </div>
      </form>
    </section>
  );
}
