"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import IncidentSummary from "@/components/incidents/IncidentSummary";
import IncidentUpload from "@/components/incidents/IncidentUpload";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import { useApiState } from "@/hooks/useApiState";
import { analyzeIncidentFile, downloadIncidentResults } from "@/lib/incidents-api";
import {
  createManagerIncident,
  getManagerIncidentSummary,
  listManagerIncidents,
  updateManagerIncidentStatus,
} from "@/lib/incidents-manager-api";
import { IncidentAnalysisResult } from "@/types/incidents";
import {
  IncidentManagerBranch,
  IncidentManagerCategory,
  IncidentManagerOrigin,
  IncidentManagerRecord,
  IncidentManagerStatus,
  IncidentManagerSummary,
} from "@/types/incidents-manager";

const MANAGER_STATUS_OPTIONS: IncidentManagerStatus[] = [
  "open",
  "in_progress",
  "resolved",
  "discarded",
];
const MANAGER_ORIGIN_OPTIONS: IncidentManagerOrigin[] = ["customer", "branch", "internal"];
const MANAGER_CATEGORY_OPTIONS: IncidentManagerCategory[] = [
  "equipment_failure",
  "supply_issue",
  "customer_complaint",
  "staff_issue",
  "facility_issue",
  "pos_system",
  "delivery_issue",
  "other",
];
const MANAGER_BRANCH_OPTIONS: IncidentManagerBranch[] = [
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

function statusBadgeClass(status: IncidentManagerStatus): string {
  if (status === "open") {
    return "border-emerald-400/40 bg-emerald-500/20 text-emerald-200";
  }
  if (status === "resolved") {
    return "border-amber-400/40 bg-amber-500/20 text-amber-100";
  }
  if (status === "discarded") {
    return "border-red-500/40 bg-red-500/20 text-red-200";
  }
  return "border-cyan-500/40 bg-cyan-500/20 text-cyan-200";
}

export default function IncidentsPage(): React.JSX.Element {
  const {
    data: result,
    state,
    error,
    execute,
  } = useApiState<IncidentAnalysisResult>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [managerItems, setManagerItems] = useState<IncidentManagerRecord[]>([]);
  const [managerSummary, setManagerSummary] = useState<IncidentManagerSummary | null>(null);
  const [managerLoading, setManagerLoading] = useState(true);
  const [managerError, setManagerError] = useState<string | null>(null);
  const [managerStatusFilter, setManagerStatusFilter] = useState<IncidentManagerStatus | "">("");
  const [creatingManagerIncident, setCreatingManagerIncident] = useState(false);
  const [updatingManagerIncidentId, setUpdatingManagerIncidentId] = useState<number | null>(null);
  const [newIncidentTitle, setNewIncidentTitle] = useState("");
  const [newIncidentDescription, setNewIncidentDescription] = useState("");
  const [newIncidentCategory, setNewIncidentCategory] =
    useState<IncidentManagerCategory>("equipment_failure");
  const [newIncidentOrigin, setNewIncidentOrigin] = useState<IncidentManagerOrigin>("branch");
  const [newIncidentBranch, setNewIncidentBranch] = useState<IncidentManagerBranch>("central");
  const router = useRouter();

  const loading = state === "loading";

  const handleAnalyze = async (file: File): Promise<void> => {
    setDownloadError(null);
    try {
      await execute(() => analyzeIncidentFile(file));
    } catch {
      // Error state is captured by useApiState; surfaced via ErrorState below.
    }
  };

  const handleDownload = async (): Promise<void> => {
    setDownloading(true);
    setDownloadError(null);
    try {
      const blob = await downloadIncidentResults();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "results.csv";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setDownloadError(
        caught instanceof Error ? caught.message : "Download failed. Please try again.",
      );
    } finally {
      setDownloading(false);
    }
  };

  const loadManagerData = useCallback(async (): Promise<void> => {
    setManagerLoading(true);
    setManagerError(null);
    try {
      const [list, summary] = await Promise.all([
        listManagerIncidents({ status: managerStatusFilter }),
        getManagerIncidentSummary(),
      ]);
      setManagerItems(list);
      setManagerSummary(summary);
    } catch (caught) {
      setManagerError(caught instanceof Error ? caught.message : "Failed to load incident manager data.");
    } finally {
      setManagerLoading(false);
    }
  }, [managerStatusFilter]);

  useEffect(() => {
    void loadManagerData();
  }, [loadManagerData]);

  const handleManagerStatusChange = async (
    incidentId: number,
    nextStatus: IncidentManagerStatus,
  ): Promise<void> => {
    setManagerError(null);
    setUpdatingManagerIncidentId(incidentId);
    try {
      await updateManagerIncidentStatus(incidentId, nextStatus);
      await loadManagerData();
    } catch (caught) {
      setManagerError(caught instanceof Error ? caught.message : "Failed to update incident status.");
    } finally {
      setUpdatingManagerIncidentId(null);
    }
  };

  const handleManagerCreate = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setManagerError(null);
    setCreatingManagerIncident(true);
    try {
      await createManagerIncident({
        title: newIncidentTitle,
        description: newIncidentDescription,
        category: newIncidentCategory,
        origin: newIncidentOrigin,
        branch: newIncidentBranch,
        status: "open",
      });
      setNewIncidentTitle("");
      setNewIncidentDescription("");
      await loadManagerData();
    } catch (caught) {
      setManagerError(caught instanceof Error ? caught.message : "Failed to create incident.");
    } finally {
      setCreatingManagerIncident(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-8 text-stone-100 md:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20">
          <p className="text-sm uppercase tracking-[0.12em] text-amber-300">
            Brasaland Incident Operations
          </p>
          <h1 className="mt-2 text-2xl font-extrabold text-amber-100 md:text-3xl">
            Analyzer + Manager
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-stone-300">
            Upload incident CSV files for analysis and manage centralized incidents from the same screen.
          </p>
        </header>

        <IncidentUpload onFileSelected={handleAnalyze} disabled={loading} />

        {loading ? <LoadingState label="Analyzing file..." /> : null}

        {error ? (
          <ErrorState
            message={error}
            showHomeLink={false}
          />
        ) : null}

        {result ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-stone-300">
                Last analyzed file:{" "}
                <span className="font-semibold text-amber-100">
                  {result?.sourcePath ?? "Unknown file"}
                </span>
              </p>
              <button
                type="button"
                onClick={handleDownload}
                disabled={downloading}
                className="rounded-xl border border-amber-300 bg-amber-300/15 px-4 py-2 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/25 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {downloading ? "Preparing download..." : "Download results CSV"}
              </button>
            </div>
            {downloadError ? (
              <ErrorState
                message={downloadError}
                onRetry={() => void handleDownload()}
                showHomeLink={false}
              />
            ) : null}
            <IncidentSummary result={result} />
          </>
        ) : null}

        <section className="rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm uppercase tracking-[0.12em] text-amber-300">Incident Manager</p>
              <h2 className="mt-1 text-xl font-extrabold text-amber-100">Seeded Incident Records</h2>
            </div>
            <label className="text-xs uppercase tracking-[0.12em] text-stone-300">
              Status filter
              <select
                value={managerStatusFilter}
                onChange={(event) =>
                  setManagerStatusFilter(event.target.value as IncidentManagerStatus | "")
                }
                className="ml-2 rounded-lg border border-stone-600 bg-stone-900 px-2 py-1 text-xs text-stone-100"
              >
                <option value="">all</option>
                {MANAGER_STATUS_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {toLabel(option)}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <article className="rounded-lg border border-emerald-500/30 bg-emerald-900/20 p-3">
              <p className="text-xs uppercase tracking-[0.12em] text-emerald-200">Open</p>
              <p className="mt-1 text-2xl font-extrabold text-emerald-100">
                {managerSummary?.by_status?.open ?? 0}
              </p>
            </article>
            <article className="rounded-lg border border-cyan-500/30 bg-cyan-900/20 p-3">
              <p className="text-xs uppercase tracking-[0.12em] text-cyan-200">In Progress</p>
              <p className="mt-1 text-2xl font-extrabold text-cyan-100">
                {managerSummary?.by_status?.in_progress ?? 0}
              </p>
            </article>
            <article className="rounded-lg border border-amber-500/30 bg-amber-900/20 p-3">
              <p className="text-xs uppercase tracking-[0.12em] text-amber-200">Resolved</p>
              <p className="mt-1 text-2xl font-extrabold text-amber-100">
                {managerSummary?.by_status?.resolved ?? 0}
              </p>
            </article>
            <article className="rounded-lg border border-red-500/30 bg-red-900/20 p-3">
              <p className="text-xs uppercase tracking-[0.12em] text-red-200">Discarded</p>
              <p className="mt-1 text-2xl font-extrabold text-red-100">
                {managerSummary?.by_status?.discarded ?? 0}
              </p>
            </article>
          </div>

          <form
            onSubmit={(event) => void handleManagerCreate(event)}
            className="mt-4 grid gap-3 rounded-xl border border-stone-700 bg-stone-900/60 p-4 md:grid-cols-2"
          >
            <input
              required
              value={newIncidentTitle}
              onChange={(event) => setNewIncidentTitle(event.target.value)}
              placeholder="Incident title"
              className="rounded-lg border border-stone-600 bg-stone-950 px-3 py-2 text-sm text-stone-100"
            />
            <select
              value={newIncidentCategory}
              onChange={(event) => setNewIncidentCategory(event.target.value as IncidentManagerCategory)}
              className="rounded-lg border border-stone-600 bg-stone-950 px-3 py-2 text-sm text-stone-100"
            >
              {MANAGER_CATEGORY_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {toLabel(option)}
                </option>
              ))}
            </select>
            <select
              value={newIncidentOrigin}
              onChange={(event) => setNewIncidentOrigin(event.target.value as IncidentManagerOrigin)}
              className="rounded-lg border border-stone-600 bg-stone-950 px-3 py-2 text-sm text-stone-100"
            >
              {MANAGER_ORIGIN_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {toLabel(option)}
                </option>
              ))}
            </select>
            <select
              value={newIncidentBranch}
              onChange={(event) => setNewIncidentBranch(event.target.value as IncidentManagerBranch)}
              className="rounded-lg border border-stone-600 bg-stone-950 px-3 py-2 text-sm text-stone-100"
            >
              {MANAGER_BRANCH_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {toLabel(option)}
                </option>
              ))}
            </select>
            <textarea
              required
              value={newIncidentDescription}
              onChange={(event) => setNewIncidentDescription(event.target.value)}
              placeholder="Description"
              rows={3}
              className="rounded-lg border border-stone-600 bg-stone-950 px-3 py-2 text-sm text-stone-100 md:col-span-2"
            />
            <button
              type="submit"
              disabled={creatingManagerIncident}
              className="rounded-lg border border-amber-300 bg-amber-300/20 px-3 py-2 text-sm font-semibold text-amber-100 disabled:cursor-not-allowed disabled:opacity-60 md:col-span-2"
            >
              {creatingManagerIncident ? "Creating incident..." : "Create incident"}
            </button>
          </form>

          {managerLoading ? <LoadingState label="Loading incident records..." /> : null}
          {managerError ? (
            <div className="mt-4">
              <ErrorState
                message={managerError}
                onRetry={() => void loadManagerData()}
                showHomeLink={false}
              />
            </div>
          ) : null}

          <div className="mt-4 overflow-hidden rounded-xl border border-stone-700">
            <table className="w-full text-left text-sm">
              <thead className="bg-stone-900 text-stone-300">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Title</th>
                  <th className="px-3 py-2">Category</th>
                  <th className="px-3 py-2">Origin</th>
                  <th className="px-3 py-2">Branch</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Update</th>
                </tr>
              </thead>
              <tbody>
                {managerItems.map((item) => (
                  <tr
                    key={item.id}
                    className="cursor-pointer border-t border-stone-800 transition hover:bg-stone-900/70"
                    onClick={() => router.push(`/incidents/${item.id}`)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        router.push(`/incidents/${item.id}`);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    aria-label={`View incident ${item.id} details`}
                  >
                    <td className="px-3 py-2">{item.id}</td>
                    <td className="px-3 py-2">{item.title}</td>
                    <td className="px-3 py-2">{toLabel(item.category)}</td>
                    <td className="px-3 py-2">{toLabel(item.origin)}</td>
                    <td className="px-3 py-2">{toLabel(item.branch)}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded-full border px-2 py-1 text-xs font-semibold uppercase tracking-[0.08em] ${statusBadgeClass(item.status)}`}
                      >
                        {toLabel(item.status)}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <select
                        value={item.status}
                        onChange={(event) =>
                          void handleManagerStatusChange(
                            item.id,
                            event.target.value as IncidentManagerStatus,
                          )
                        }
                        onClick={(event) => event.stopPropagation()}
                        onKeyDown={(event) => event.stopPropagation()}
                        disabled={updatingManagerIncidentId === item.id}
                        className="rounded-lg border border-stone-600 bg-stone-900 px-2 py-1 text-xs text-stone-100"
                      >
                        {MANAGER_STATUS_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {toLabel(option)}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
                {!managerLoading && managerItems.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-3 py-4 text-center text-stone-400">
                      No incidents found for the selected filter.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
