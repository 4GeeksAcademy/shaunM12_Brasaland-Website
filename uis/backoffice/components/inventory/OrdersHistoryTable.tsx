"use client";

import ErrorState from "@/components/ui/ErrorState";
import {
  ALL_RESTAURANTS_LOCATION_ID,
  COUNTRY_LABELS,
  INPUT_CLASS,
  LABEL_CLASS,
  formatLocationLabel,
  getLocationsForCountry,
} from "@/lib/inventory-constants";
import { OrderHistoryRow, ProductCountry } from "@/types/inventory";

interface OrdersHistoryTableProps {
  rows: OrderHistoryRow[];
  loading: boolean;
  error: string | null;
  locationId: number;
  onLocationChange: (locationId: number) => void;
  onRetry?: () => void;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function formatQuantity(row: OrderHistoryRow): string {
  const amount = Number.isInteger(row.quantity)
    ? String(row.quantity)
    : row.quantity.toFixed(1);
  return row.unit ? `${amount} ${row.unit}` : amount;
}

function TypeBadge({ kind }: { kind: OrderHistoryRow["kind"] }): React.JSX.Element {
  const isInbound = kind === "inbound";
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${
        isInbound
          ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/40"
          : "bg-orange-500/15 text-orange-300 ring-1 ring-orange-400/40"
      }`}
    >
      {isInbound ? "Inbound" : "Outbound"}
    </span>
  );
}

function summaryLabel(locationId: number, count: number): string {
  const noun = `${count} order${count === 1 ? "" : "s"}`;
  if (locationId === ALL_RESTAURANTS_LOCATION_ID) {
    return `${noun} across all restaurants (read-only)`;
  }
  return `${noun} at ${formatLocationLabel(locationId)} (read-only)`;
}

export default function OrdersHistoryTable({
  rows,
  loading,
  error,
  locationId,
  onLocationChange,
  onRetry,
}: OrdersHistoryTableProps): React.JSX.Element {
  const showLocationColumn = locationId === ALL_RESTAURANTS_LOCATION_ID;

  if (error) {
    return <ErrorState message={error} onRetry={onRetry} showHomeLink={false} />;
  }

  return (
    <section className="space-y-4">
      <label className="block w-full sm:max-w-md">
        <span className={LABEL_CLASS}>Restaurant</span>
        <select
          value={locationId}
          onChange={(event) => onLocationChange(Number(event.target.value))}
          className={INPUT_CLASS}
        >
          <option value={ALL_RESTAURANTS_LOCATION_ID}>All restaurants</option>
          {(["CO", "US"] as ProductCountry[]).map((country) => (
            <optgroup key={country} label={COUNTRY_LABELS[country]}>
              {getLocationsForCountry(country).map((location) => (
                <option key={location.id} value={location.id}>
                  {location.name} — {location.city}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>

      <div className="overflow-hidden rounded-xl border border-amber-200/20 bg-stone-900/85">
        <div className="border-b border-amber-200/10 px-4 py-3 text-xs text-stone-400">
          {loading ? "Loading orders..." : summaryLabel(locationId, rows.length)}
        </div>

        {loading ? (
          <p className="px-4 py-8 text-sm text-stone-400">Fetching order history…</p>
        ) : rows.length === 0 ? (
          <p className="px-4 py-8 text-sm text-stone-400">
            {locationId === ALL_RESTAURANTS_LOCATION_ID
              ? "No orders recorded yet."
              : "No orders recorded for this restaurant yet."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-stone-950/60 text-xs uppercase tracking-[0.08em] text-stone-400">
                <tr>
                  <th className="px-4 py-3 font-semibold">Type</th>
                  <th className="px-4 py-3 font-semibold">Product</th>
                  <th className="px-4 py-3 font-semibold">Quantity</th>
                  {showLocationColumn ? (
                    <th className="px-4 py-3 font-semibold">Restaurant</th>
                  ) : null}
                  <th className="px-4 py-3 font-semibold">Details</th>
                  <th className="px-4 py-3 font-semibold">Date</th>
                  <th className="px-4 py-3 font-semibold">Created by</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-800/80">
                {rows.map((row) => (
                  <tr key={`${row.kind}-${row.id}`} className="text-stone-200">
                    <td className="px-4 py-3">
                      <TypeBadge kind={row.kind} />
                    </td>
                    <td className="px-4 py-3 font-medium text-amber-50">{row.ingredient_name}</td>
                    <td className="px-4 py-3">{formatQuantity(row)}</td>
                    {showLocationColumn ? (
                      <td className="px-4 py-3 text-xs text-stone-400">
                        {formatLocationLabel(row.location_id)}
                      </td>
                    ) : null}
                    <td className="px-4 py-3 text-stone-400">
                      {row.kind === "inbound"
                        ? `Supplier: ${row.supplier_name ?? "—"}`
                        : `Reason: ${row.reason ?? "—"}`}
                    </td>
                    <td className="px-4 py-3 text-stone-300">{formatDate(row.created_at)}</td>
                    <td className="px-4 py-3 font-mono text-xs text-stone-400">{row.user_uuid}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
