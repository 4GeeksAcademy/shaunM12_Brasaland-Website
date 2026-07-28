"use client";

import { useMemo, useState } from "react";
import { IncidentManagerSummary } from "@/types/incidents";

const BRANCH_LABELS: Record<string, string> = {
  central: "Central (Medellin / Miami)",
  medellin_centro: "Medellin Centro",
  medellin_laureles: "Medellin Laureles",
  medellin_envigado: "Medellin Envigado",
  medellin_bello: "Medellin Bello",
  medellin_itagui: "Medellin Itagui",
  bogota_chapinero: "Bogota Chapinero",
  bogota_usaquen: "Bogota Usaquen",
  cali_granada: "Cali Granada",
  barranquilla_norte: "Barranquilla Norte",
  miami_doral: "Miami Doral",
  miami_hialeah: "Miami Hialeah",
  miami_kendall: "Miami Kendall",
  orlando_international: "Orlando International Drive",
  fort_lauderdale: "Fort Lauderdale",
};

const CATEGORY_LABELS: Record<string, string> = {
  equipment_failure: "Equipment failure",
  supply_issue: "Supply issue",
  customer_complaint: "Customer complaint",
  staff_issue: "Staff issue",
  facility_issue: "Facility issue",
  pos_system: "POS system",
  delivery_issue: "Delivery issue",
  other: "Other",
};

const ORIGIN_LABELS: Record<string, string> = {
  customer: "Customer",
  branch: "Branch",
  internal: "Internal",
};

const STATUS_ORDER = ["open", "in_progress", "resolved", "discarded"] as const;

const STATUS_LABELS: Record<string, string> = {
  open: "Open",
  in_progress: "In progress",
  resolved: "Resolved",
  discarded: "Discarded",
};

function humanize(key: string, labels: Record<string, string>): string {
  return labels[key] ?? key.replaceAll("_", " ");
}

function rankedEntries(
  values: Record<string, number> | undefined,
  labels: Record<string, string>,
  options?: { hideZeros?: boolean },
): { key: string; label: string; count: number }[] {
  const hideZeros = options?.hideZeros ?? false;
  return Object.entries(values ?? {})
    .filter(([, count]) => !hideZeros || count > 0)
    .map(([key, count]) => ({
      key,
      label: humanize(key, labels),
      count,
    }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
}

function RankedList({
  title,
  entries,
  emptyLabel,
  maxVisible,
}: {
  title: string;
  entries: { key: string; label: string; count: number }[];
  emptyLabel: string;
  maxVisible?: number;
}): React.JSX.Element {
  const [showAll, setShowAll] = useState(false);
  const visible =
    maxVisible && !showAll ? entries.slice(0, maxVisible) : entries;
  const hiddenCount =
    maxVisible && entries.length > maxVisible
      ? entries.length - maxVisible
      : 0;

  return (
    <div>
      <h3 className="text-xs uppercase tracking-[0.1em] text-[color:var(--bo-accent-muted)]/80">
        {title}
      </h3>
      {entries.length === 0 ? (
        <p className="mt-2 text-sm bo-muted">{emptyLabel}</p>
      ) : (
        <>
          <ul className="mt-2 space-y-1.5 text-sm bo-muted">
            {visible.map((entry) => (
              <li key={entry.key} className="flex justify-between gap-4">
                <span>{entry.label}</span>
                <span className="font-semibold text-[color:var(--bo-heading)]">{entry.count}</span>
              </li>
            ))}
          </ul>
          {hiddenCount > 0 ? (
            <button
              type="button"
              onClick={() => setShowAll((current) => !current)}
              className="mt-2 text-xs font-semibold uppercase tracking-[0.1em] text-[color:var(--bo-accent-muted)]/80 hover:text-[color:var(--bo-heading)]"
            >
              {showAll ? "Show less" : `Show ${hiddenCount} more`}
            </button>
          ) : null}
        </>
      )}
    </div>
  );
}

export default function IncidentManagerSummaryPanel({
  summary,
  loading,
  error,
}: {
  summary: IncidentManagerSummary | null;
  loading: boolean;
  error: string | null;
}): React.JSX.Element {
  const statusPulse = useMemo(() => {
    const byStatus = summary?.by_status ?? {};
    const total = Object.values(byStatus).reduce((sum, value) => sum + value, 0);
    return {
      total,
      items: STATUS_ORDER.map((key) => ({
        key,
        label: STATUS_LABELS[key],
        count: byStatus[key] ?? 0,
      })),
    };
  }, [summary]);

  const originEntries = useMemo(
    () => rankedEntries(summary?.by_origin, ORIGIN_LABELS, { hideZeros: true }),
    [summary],
  );
  const categoryEntries = useMemo(
    () =>
      rankedEntries(summary?.by_category, CATEGORY_LABELS, { hideZeros: true }),
    [summary],
  );
  const branchEntries = useMemo(
    () => rankedEntries(summary?.by_branch, BRANCH_LABELS, { hideZeros: true }),
    [summary],
  );

  return (
    <section className="rounded-2xl border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-panel)] p-5">
      <div className="flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
        <h2 className="text-lg font-semibold text-[color:var(--bo-heading)]">Operations summary</h2>
        {!loading && !error && summary ? (
          <p className="text-xs uppercase tracking-[0.1em] bo-muted">
            {statusPulse.total} total incidents
          </p>
        ) : null}
      </div>

      {loading ? (
        <p className="mt-3 text-sm bo-muted">Loading summary…</p>
      ) : null}
      {error ? (
        <p className="mt-3 text-sm text-[color:var(--bo-error-fg)]">
          Summary unavailable: {error}. The rest of this page still works.
        </p>
      ) : null}

      {!loading && !error && summary ? (
        <div className="mt-4 space-y-5">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            <div className="bo-stat-accent px-3 py-3">
              <p className="text-[0.65rem] uppercase tracking-[0.12em] text-[color:var(--bo-accent-muted)]/80">
                Total
              </p>
              <p className="mt-1 text-2xl font-extrabold text-[color:var(--bo-heading)]">
                {statusPulse.total}
              </p>
            </div>
            {statusPulse.items.map((item) => (
              <div
                key={item.key}
                className="rounded-xl border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-card)] px-3 py-3"
              >
                <p className="text-[0.65rem] uppercase tracking-[0.12em] bo-muted">
                  {item.label}
                </p>
                <p className="mt-1 text-2xl font-extrabold text-[color:var(--bo-fg)]">
                  {item.count}
                </p>
              </div>
            ))}
          </div>

          {originEntries.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {originEntries.map((entry) => (
                <span
                  key={entry.key}
                  className="rounded-full border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-card)] px-3 py-1 text-xs bo-fg-secondary"
                >
                  {entry.label}:{" "}
                  <span className="font-semibold text-[color:var(--bo-heading)]">{entry.count}</span>
                </span>
              ))}
            </div>
          ) : null}

          <div className="grid gap-6 md:grid-cols-2">
            <RankedList
              title="By category"
              entries={categoryEntries}
              emptyLabel="No category activity yet."
            />
            <RankedList
              title="By branch"
              entries={branchEntries}
              emptyLabel="No branch activity yet."
              maxVisible={5}
            />
          </div>
        </div>
      ) : null}

      {!loading && !error && !summary ? (
        <p className="mt-3 text-sm bo-muted">No summary loaded yet.</p>
      ) : null}
    </section>
  );
}
