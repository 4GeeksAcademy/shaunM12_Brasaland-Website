"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ManagedIncident,
  ManagedIncidentStatus,
  STATUS_TRANSITIONS,
} from "@/types/incidents";
import { updateManagedIncidentStatus } from "@/lib/incidents-api";

const PAGE_SIZE = 10;

export default function IncidentManagerList({
  incidents,
  loading,
  error,
  onUpdated,
}: {
  incidents: ManagedIncident[] | null;
  loading: boolean;
  error: string | null;
  onUpdated: (incident: ManagedIncident) => void;
}): React.JSX.Element {
  const [rowError, setRowError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  const total = incidents?.length ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    setPage((current) => Math.min(current, totalPages));
  }, [totalPages]);

  useEffect(() => {
    // New rows (or a full reload that changes count) should surface from page 1.
    setPage(1);
  }, [total]);

  const pageItems = useMemo(() => {
    if (!incidents || incidents.length === 0) {
      return [];
    }
    const safePage = Math.min(Math.max(page, 1), totalPages);
    const start = (safePage - 1) * PAGE_SIZE;
    return incidents.slice(start, start + PAGE_SIZE);
  }, [incidents, page, totalPages]);

  const handleStatusChange = async (
    incident: ManagedIncident,
    nextStatus: ManagedIncidentStatus,
  ): Promise<void> => {
    if (nextStatus === incident.status) {
      return;
    }
    setRowError(null);
    setPendingId(incident.id);
    const previous = incident.status;
    // Optimistic update for immediate feedback; revert if the request fails.
    onUpdated({ ...incident, status: nextStatus });
    try {
      const updated = await updateManagedIncidentStatus(incident.id, nextStatus);
      onUpdated(updated);
    } catch (caught) {
      onUpdated({ ...incident, status: previous });
      setRowError(
        caught instanceof Error
          ? caught.message
          : "Status update failed. The previous status was restored.",
      );
    } finally {
      setPendingId(null);
    }
  };

  if (loading) {
    return (
      <section className="rounded-2xl border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-panel)] p-5">
        <h2 className="text-lg font-semibold text-[color:var(--bo-heading)]">Incident list</h2>
        <p className="mt-3 text-sm bo-muted">Loading incidents…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-2xl border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-panel)] p-5">
        <h2 className="text-lg font-semibold text-[color:var(--bo-heading)]">Incident list</h2>
        <p className="mt-3 text-sm text-[color:var(--bo-error-fg)]">{error}</p>
      </section>
    );
  }

  if (!incidents || incidents.length === 0) {
    return (
      <section className="rounded-2xl border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-panel)] p-5">
        <h2 className="text-lg font-semibold text-[color:var(--bo-heading)]">Incident list</h2>
        <p className="mt-3 text-sm bo-muted">
          No incidents yet. Create one above or seed historical CSV rows.
        </p>
      </section>
    );
  }

  const rangeStart = (page - 1) * PAGE_SIZE + 1;
  const rangeEnd = Math.min(page * PAGE_SIZE, total);

  return (
    <section className="overflow-x-auto rounded-2xl border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-panel)]">
      <div className="flex flex-col gap-2 border-b border-[color:var(--bo-panel-border)] px-5 py-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[color:var(--bo-heading)]">Incident list</h2>
          <p className="mt-1 text-xs bo-muted">
            Showing {rangeStart}–{rangeEnd} of {total}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            className="rounded-full border border-[color:var(--bo-card-border)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-[color:var(--bo-heading)] transition hover:border-[color:var(--bo-accent-border)] disabled:cursor-not-allowed disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-xs bo-muted">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
            className="rounded-full border border-[color:var(--bo-card-border)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-[color:var(--bo-heading)] transition hover:border-[color:var(--bo-accent-border)] disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
      {rowError ? (
        <p className="px-5 pt-3 text-sm text-[color:var(--bo-error-fg)]">{rowError}</p>
      ) : null}
      <table className="bo-table">
        <thead className="border-b border-[color:var(--bo-panel-border)] text-xs uppercase tracking-[0.1em] text-[color:var(--bo-accent-muted)]/80">
          <tr>
            <th className="px-4 py-3">ID</th>
            <th className="px-4 py-3">Title</th>
            <th className="px-4 py-3">Branch</th>
            <th className="px-4 py-3">Category</th>
            <th className="px-4 py-3">Origin</th>
            <th className="px-4 py-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {pageItems.map((incident) => {
            const options = [
              incident.status,
              ...STATUS_TRANSITIONS[incident.status].filter(
                (value) => value !== incident.status,
              ),
            ];
            return (
              <tr key={incident.id} className="border-b border-[color:var(--bo-panel-border)]">
                <td className="px-4 py-3 bo-muted">{incident.id}</td>
                <td className="px-4 py-3 text-[color:var(--bo-fg)]">{incident.title}</td>
                <td className="px-4 py-3 bo-muted">{incident.branch}</td>
                <td className="px-4 py-3 bo-muted">{incident.category}</td>
                <td className="px-4 py-3 bo-muted">{incident.origin}</td>
                <td className="px-4 py-3">
                  <select
                    className="rounded-lg border border-[color:var(--bo-card-border)] bg-[color:var(--bo-card)] px-2 py-1 text-[color:var(--bo-fg)] disabled:opacity-50"
                    value={incident.status}
                    disabled={pendingId === incident.id || options.length === 1}
                    onChange={(event) => {
                      void handleStatusChange(
                        incident,
                        event.target.value as ManagedIncidentStatus,
                      );
                    }}
                  >
                    {options.map((status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
