"use client";

import { useCallback, useEffect, useState } from "react";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import {
  createManagerIncident,
  getManagerIncidentSummary,
  listManagerIncidents,
  updateManagerIncidentStatus,
} from "@/lib/incidents-manager-api";
import {
  IncidentManagerBranch,
  IncidentManagerCategory,
  IncidentManagerOrigin,
  IncidentManagerRecord,
  IncidentManagerStatus,
  IncidentManagerSummary,
} from "@/types/incidents-manager";

const STATUS_OPTIONS: IncidentManagerStatus[] = [
  "open",
  "in_progress",
  "resolved",
  "discarded",
];

const ORIGIN_OPTIONS: IncidentManagerOrigin[] = ["customer", "branch", "internal"];

const CATEGORY_OPTIONS: IncidentManagerCategory[] = [
  "equipment_failure",
  "supply_issue",
  "customer_complaint",
  "staff_issue",
  "facility_issue",
  "pos_system",
  "delivery_issue",
  "other",
];

const BRANCH_OPTIONS: IncidentManagerBranch[] = [
  "central",
  "medellin_centro",
  "medellin_laureles",
  "medellin_envigado",
  "medellin_bello",
  "medellin_itagui",
  "bogota_chapinero",
  "bogota_usaquen",
  "cali_granada",
  "barranquilla_norte",
  "miami_doral",
  "miami_hialeah",
  "miami_kendall",
  "orlando_international",
  "fort_lauderdale",
];

function toLabel(value: string): string {
  return value.replaceAll("_", " ");
}

export default function IncidentManagerPage(): React.JSX.Element {
  const [items, setItems] = useState<IncidentManagerRecord[]>([]);
  const [summary, setSummary] = useState<IncidentManagerSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [statusFilter, setStatusFilter] = useState<IncidentManagerStatus | "">("");

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<IncidentManagerCategory>("equipment_failure");
  const [origin, setOrigin] = useState<IncidentManagerOrigin>("branch");
  const [branch, setBranch] = useState<IncidentManagerBranch>("central");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [list, metrics] = await Promise.all([
        listManagerIncidents({ status: statusFilter }),
        getManagerIncidentSummary(),
      ]);
      setItems(list);
      setSummary(metrics);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load incident manager data.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createManagerIncident({
        title,
        description,
        category,
        origin,
        branch,
        status: "open",
      });
      setTitle("");
      setDescription("");
      await loadData();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to create incident.");
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (
    incidentId: number,
    nextStatus: IncidentManagerStatus,
  ): Promise<void> => {
    setError(null);
    try {
      await updateManagerIncidentStatus(incidentId, nextStatus);
      await loadData();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to update status.");
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-8 text-stone-100 md:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20">
          <p className="text-sm uppercase tracking-[0.12em] text-amber-300">Brasaland Incident Manager</p>
          <h1 className="mt-2 text-2xl font-extrabold text-amber-100 md:text-3xl">
            Centralized Incident Operations
          </h1>
          <p className="mt-2 text-sm text-stone-300">
            Create and manage incidents from the `/api/incidents` manager endpoints.
          </p>
        </header>

        <section className="grid gap-4 rounded-xl border border-amber-200/20 bg-stone-900/85 p-4 md:grid-cols-4">
          <label className="text-sm text-stone-100">
            Filter by status
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as IncidentManagerStatus | "")}
              className="mt-1 w-full rounded-xl border border-stone-600 bg-stone-950/80 px-3 py-2 text-stone-100"
            >
              <option value="">All</option>
              {STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {toLabel(option)}
                </option>
              ))}
            </select>
          </label>

          <div className="rounded-lg border border-emerald-500/30 bg-emerald-900/20 p-3">
            <p className="text-xs uppercase tracking-[0.12em] text-emerald-200">Open</p>
            <p className="mt-1 text-2xl font-extrabold text-emerald-100">{summary?.by_status?.open ?? 0}</p>
          </div>

          <div className="rounded-lg border border-cyan-500/30 bg-cyan-900/20 p-3">
            <p className="text-xs uppercase tracking-[0.12em] text-cyan-200">In Progress</p>
            <p className="mt-1 text-2xl font-extrabold text-cyan-100">{summary?.by_status?.in_progress ?? 0}</p>
          </div>

          <div className="rounded-lg border border-amber-500/30 bg-amber-900/20 p-3">
            <p className="text-xs uppercase tracking-[0.12em] text-amber-200">Resolved</p>
            <p className="mt-1 text-2xl font-extrabold text-amber-100">{summary?.by_status?.resolved ?? 0}</p>
          </div>
        </section>

        <section className="rounded-xl border border-stone-700 bg-stone-950/70 p-4">
          <h2 className="text-lg font-semibold text-amber-200">Create incident</h2>
          <form onSubmit={(event) => void handleCreate(event)} className="mt-3 grid gap-3 md:grid-cols-2">
            <input
              required
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Incident title"
              className="rounded-xl border border-stone-600 bg-stone-900 px-3 py-2 text-sm"
            />
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value as IncidentManagerCategory)}
              className="rounded-xl border border-stone-600 bg-stone-900 px-3 py-2 text-sm"
            >
              {CATEGORY_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {toLabel(option)}
                </option>
              ))}
            </select>
            <select
              value={origin}
              onChange={(event) => setOrigin(event.target.value as IncidentManagerOrigin)}
              className="rounded-xl border border-stone-600 bg-stone-900 px-3 py-2 text-sm"
            >
              {ORIGIN_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {toLabel(option)}
                </option>
              ))}
            </select>
            <select
              value={branch}
              onChange={(event) => setBranch(event.target.value as IncidentManagerBranch)}
              className="rounded-xl border border-stone-600 bg-stone-900 px-3 py-2 text-sm"
            >
              {BRANCH_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {toLabel(option)}
                </option>
              ))}
            </select>
            <textarea
              required
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Description"
              className="rounded-xl border border-stone-600 bg-stone-900 px-3 py-2 text-sm md:col-span-2"
              rows={3}
            />
            <button
              type="submit"
              disabled={saving}
              className="rounded-xl border border-amber-300 bg-amber-300/20 px-4 py-2 text-sm font-semibold text-amber-100 disabled:cursor-not-allowed disabled:opacity-60 md:col-span-2"
            >
              {saving ? "Creating..." : "Create Incident"}
            </button>
          </form>
        </section>

        {loading ? <LoadingState label="Loading incident manager..." /> : null}
        {error ? <ErrorState message={error} onRetry={() => void loadData()} showHomeLink={false} /> : null}

        <section className="overflow-hidden rounded-xl border border-stone-700 bg-stone-950/70">
          <table className="w-full text-left text-sm">
            <thead className="bg-stone-900 text-stone-300">
              <tr>
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Category</th>
                <th className="px-3 py-2">Branch</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Update</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-t border-stone-800">
                  <td className="px-3 py-2">{item.id}</td>
                  <td className="px-3 py-2">{item.title}</td>
                  <td className="px-3 py-2">{toLabel(item.category)}</td>
                  <td className="px-3 py-2">{toLabel(item.branch)}</td>
                  <td className="px-3 py-2">{toLabel(item.status)}</td>
                  <td className="px-3 py-2">
                    <select
                      value={item.status}
                      onChange={(event) =>
                        void handleStatusChange(item.id, event.target.value as IncidentManagerStatus)
                      }
                      className="rounded-lg border border-stone-600 bg-stone-900 px-2 py-1 text-xs"
                    >
                      {STATUS_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {toLabel(option)}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
              {!items.length ? (
                <tr>
                  <td colSpan={6} className="px-3 py-4 text-center text-stone-400">
                    No incidents found for current filters.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}
