import { redirect } from "next/navigation";

/** Canonical inventory UI lives under `/inventory/*`; entry redirects to products. */
export default function InventoryIndexPage(): never {
  redirect("/inventory/products");
}
