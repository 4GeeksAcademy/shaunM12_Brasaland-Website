"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useOrderFormAbandonment } from "@/hooks/useOrderFormAbandonment";
import {
  INPUT_CLASS,
  LABEL_CLASS,
  RESTAURANT_LOCATIONS,
  formatLocationLabel,
  getQuantityConstraints,
  isValidQuantity,
} from "@/lib/inventory-constants";
import {
  filterSuppliersForInbound,
  pickDefaultSupplier,
} from "@/lib/inventory-supplier-utils";
import { createInboundOrder } from "@/lib/inventory";
import { fetchSuppliers } from "@/lib/suppliers-api";
import { Product } from "@/types/inventory";
import { Supplier } from "@/types/suppliers";

interface InboundOrderFormProps {
  products: Product[];
  productsLoading: boolean;
}

const EMPTY_FORM = {
  ingredient_id: "",
  quantity: "",
  supplier_id: "",
  location_id: "",
  unit_cost: "",
};

function resolveLocationId(preferredLocationId?: string | null): number {
  const preferred = preferredLocationId
    ? RESTAURANT_LOCATIONS.find((location) => String(location.id) === preferredLocationId)
    : undefined;
  return preferred?.id ?? RESTAURANT_LOCATIONS[0]?.id ?? 1;
}

function applyProductDefaults(
  product: Product,
  suppliers: Supplier[],
  current: typeof EMPTY_FORM,
  preferredLocationId?: string | null,
): typeof EMPTY_FORM {
  const locationId = resolveLocationId(preferredLocationId);
  const defaultSupplier = pickDefaultSupplier(suppliers, product.category, locationId);
  return {
    ...current,
    ingredient_id: String(product.id),
    supplier_id: defaultSupplier ? String(defaultSupplier.id) : "",
    location_id: String(locationId),
    quantity: "",
    unit_cost: "",
  };
}

export default function InboundOrderForm({
  products,
  productsLoading,
}: InboundOrderFormProps): React.JSX.Element {
  const searchParams = useSearchParams();
  const preselectedId = searchParams.get("productId");
  const preselectedLocationId = searchParams.get("locationId");

  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [suppliersLoading, setSuppliersLoading] = useState(true);
  const [suppliersError, setSuppliersError] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const selectedProduct = useMemo(
    () => products.find((product) => String(product.id) === form.ingredient_id),
    [form.ingredient_id, products],
  );

  const locationId = Number(form.location_id) || resolveLocationId(preselectedLocationId);

  const availableSuppliers = useMemo(() => {
    if (!selectedProduct) {
      return [];
    }
    return filterSuppliersForInbound(suppliers, selectedProduct.category, locationId);
  }, [locationId, selectedProduct, suppliers]);

  const quantityConstraints = getQuantityConstraints(selectedProduct?.unit);

  const fieldsCompleted = useMemo(() => {
    const completed: string[] = [];
    if (form.ingredient_id) completed.push("product_id");
    if (form.quantity) completed.push("quantity");
    if (form.supplier_id) completed.push("supplier_id");
    if (form.location_id) completed.push("location_id");
    if (form.unit_cost) completed.push("unit_cost");
    return completed;
  }, [form.ingredient_id, form.location_id, form.quantity, form.supplier_id, form.unit_cost]);

  useOrderFormAbandonment({
    formType: "InboundOrder",
    productId: form.ingredient_id ? Number(form.ingredient_id) : null,
    locationId: Number(form.location_id) || locationId,
    fieldsCompleted,
    active: Boolean(form.ingredient_id) && !submitting && !successMessage,
  });

  useEffect(() => {
    let cancelled = false;
    setSuppliersLoading(true);
    setSuppliersError(null);
    void fetchSuppliers()
      .then((rows) => {
        if (!cancelled) {
          setSuppliers(rows);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setSuppliersError(
            caught instanceof Error
              ? caught.message
              : "Could not load supplier directory.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setSuppliersLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!preselectedId || products.length === 0 || suppliers.length === 0) {
      return;
    }
    const product = products.find((item) => String(item.id) === preselectedId);
    if (product) {
      setForm(applyProductDefaults(product, suppliers, EMPTY_FORM, preselectedLocationId));
    }
  }, [preselectedId, preselectedLocationId, products, suppliers]);

  const handleProductChange = (productId: string): void => {
    const product = products.find((item) => String(item.id) === productId);
    if (!product) {
      setForm((current) => ({ ...current, ingredient_id: productId, supplier_id: "" }));
      return;
    }
    setForm(
      applyProductDefaults(
        product,
        suppliers,
        form,
        form.location_id || preselectedLocationId,
      ),
    );
  };

  const handleLocationChange = (nextLocationId: string): void => {
    const numericId = Number(nextLocationId);
    if (!selectedProduct) {
      setForm((current) => ({ ...current, location_id: nextLocationId }));
      return;
    }
    const defaultSupplier = pickDefaultSupplier(
      suppliers,
      selectedProduct.category,
      numericId,
    );
    setForm((current) => ({
      ...current,
      location_id: nextLocationId,
      supplier_id: defaultSupplier ? String(defaultSupplier.id) : "",
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setFormError(null);
    setSuccessMessage(null);

    const ingredientId = Number(form.ingredient_id);
    const quantity = Number(form.quantity);
    const supplierId = Number(form.supplier_id);
    const orderLocationId = Number(form.location_id);
    const unitCostRaw = form.unit_cost.trim();
    const unitCost = unitCostRaw === "" ? undefined : Number(unitCostRaw);

    if (!ingredientId || !selectedProduct) {
      setFormError("Select a product.");
      return;
    }

    if (!supplierId) {
      setFormError("Select a supplier from the directory.");
      return;
    }

    if (!isValidQuantity(quantity, selectedProduct.unit)) {
      setFormError(
        `Enter a valid quantity in ${selectedProduct.unit} (min ${quantityConstraints.min}, step ${quantityConstraints.step}).`,
      );
      return;
    }

    if (unitCostRaw !== "" && (!Number.isFinite(unitCost) || (unitCost ?? 0) <= 0)) {
      setFormError("Unit cost must be a positive number when provided.");
      return;
    }

    if (!RESTAURANT_LOCATIONS.some((location) => location.id === orderLocationId)) {
      setFormError("Select a restaurant.");
      return;
    }

    setSubmitting(true);
    try {
      await createInboundOrder({
        ingredient_id: ingredientId,
        quantity,
        supplier_id: supplierId,
        location_id: orderLocationId,
        ...(unitCost !== undefined ? { unit_cost: unitCost } : {}),
      });
      const resetProduct = preselectedId
        ? products.find((item) => String(item.id) === preselectedId)
        : undefined;
      setForm(
        resetProduct
          ? applyProductDefaults(
              resetProduct,
              suppliers,
              EMPTY_FORM,
              preselectedLocationId,
            )
          : EMPTY_FORM,
      );
      setSuccessMessage(
        `Inbound delivery for ${selectedProduct.name} recorded at ${formatLocationLabel(orderLocationId)}.`,
      );
    } catch (caught) {
      const message =
        caught instanceof Error ? caught.message : "Could not record inbound order.";
      setFormError(
        message,
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

        <label>
          <span className={LABEL_CLASS}>
            Unit cost (optional, local currency)
          </span>
          <input
            type="number"
            min={0.01}
            step="0.01"
            value={form.unit_cost}
            onChange={(event) =>
              setForm((current) => ({ ...current, unit_cost: event.target.value }))
            }
            className={INPUT_CLASS}
            placeholder="e.g. 22000"
            disabled={!selectedProduct}
          />
        </label>

        <label className="md:col-span-2">
          <span className={LABEL_CLASS}>Supplier (directory)</span>
          <select
            required
            value={form.supplier_id}
            onChange={(event) =>
              setForm((current) => ({ ...current, supplier_id: event.target.value }))
            }
            className={INPUT_CLASS}
            disabled={
              !selectedProduct || suppliersLoading || availableSuppliers.length === 0
            }
          >
            <option value="">
              {suppliersLoading
                ? "Loading suppliers…"
                : availableSuppliers.length === 0
                  ? "No active suppliers for this product and location"
                  : "Select a supplier…"}
            </option>
            {availableSuppliers.map((supplier) => (
              <option key={supplier.id} value={supplier.id}>
                {supplier.name}
              </option>
            ))}
          </select>
        </label>

        {suppliersError ? (
          <p role="alert" className="md:col-span-2 text-sm text-amber-200">
            {suppliersError}
          </p>
        ) : null}

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
            disabled={
              submitting ||
              productsLoading ||
              suppliersLoading ||
              !selectedProduct ||
              !form.supplier_id
            }
            className="rounded-full bg-amber-300 px-5 py-2 text-sm font-semibold text-stone-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Saving…" : "Record inbound delivery"}
          </button>
        </div>
      </form>
    </section>
  );
}
