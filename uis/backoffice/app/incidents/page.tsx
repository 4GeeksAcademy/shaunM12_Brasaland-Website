"use client";

import { useCallback, useEffect, useState } from "react";
import IncidentManagerForm from "@/components/incidents/IncidentManagerForm";
import IncidentManagerList from "@/components/incidents/IncidentManagerList";
import IncidentManagerSummaryPanel from "@/components/incidents/IncidentManagerSummaryPanel";
import IncidentSummary from "@/components/incidents/IncidentSummary";
import IncidentUpload from "@/components/incidents/IncidentUpload";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import { useApiState } from "@/hooks/useApiState";
import {
  analyzeIncidentFile,
  downloadIncidentResults,
  fetchIncidentManagerSummary,
  listManagedIncidents,
} from "@/lib/incidents-api";
import {
  IncidentAnalysisResult,
  IncidentManagerSummary,
  ManagedIncident,
} from "@/types/incidents";

type Section = "manager" | "analyzer";

export default function IncidentsPage(): React.JSX.Element {
  const [section, setSection] = useState<Section>("manager");

  const {
    data: analyzerResult,
    state: analyzerState,
    error: analyzerError,
    execute: executeAnalyze,
  } = useApiState<IncidentAnalysisResult>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const [incidents, setIncidents] = useState<ManagedIncident[] | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [summary, setSummary] = useState<IncidentManagerSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const refreshList = useCallback(async (): Promise<void> => {
    setListLoading(true);
    setListError(null);
    try {
      const rows = await listManagedIncidents();
      setIncidents(rows);
    } catch (caught) {
      setListError(
        caught instanceof Error ? caught.message : "Could not load incidents.",
      );
    } finally {
      setListLoading(false);
    }
  }, []);

  const refreshSummary = useCallback(async (): Promise<void> => {
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      const payload = await fetchIncidentManagerSummary();
      setSummary(payload);
    } catch (caught) {
      // Soft-fail: keep the page usable when summary is down.
      setSummary(null);
      setSummaryError(
        caught instanceof Error ? caught.message : "Summary request failed.",
      );
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshList();
    void refreshSummary();
  }, [refreshList, refreshSummary]);

  const analyzerLoading = analyzerState === "loading";

  const handleAnalyze = async (file: File): Promise<void> => {
    setDownloadError(null);
    try {
      await executeAnalyze(() => analyzeIncidentFile(file));
    } catch {
      // Error state is captured by useApiState.
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

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-8 text-stone-100 md:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20">
          <p className="text-sm uppercase tracking-[0.12em] text-amber-300">
            Brasaland Incidents
          </p>
          <h1 className="mt-2 text-2xl font-extrabold text-amber-100 md:text-3xl">
            Centralized incident operations
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-stone-300">
            Manage live incidents and analyze historical CSV uploads in one place for
            Felipe and the operations team.
          </p>

          <div className="mt-5 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setSection("manager")}
              className={`rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] ${
                section === "manager"
                  ? "border-amber-300 bg-amber-300/25 text-amber-50"
                  : "border-amber-200/20 text-stone-300 hover:border-amber-200/40"
              }`}
            >
              Manager
            </button>
            <button
              type="button"
              onClick={() => setSection("analyzer")}
              className={`rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] ${
                section === "analyzer"
                  ? "border-amber-300 bg-amber-300/25 text-amber-50"
                  : "border-amber-200/20 text-stone-300 hover:border-amber-200/40"
              }`}
            >
              File analyzer
            </button>
          </div>
        </header>

        {section === "manager" ? (
          <div className="space-y-6">
            <IncidentManagerForm
              onCreated={(created) => {
                setIncidents((current) => [created, ...(current ?? [])]);
                void refreshSummary();
              }}
            />
            <IncidentManagerList
              incidents={incidents}
              loading={listLoading}
              error={listError}
              onUpdated={(updated) => {
                setIncidents((current) =>
                  (current ?? []).map((row) =>
                    row.id === updated.id ? updated : row,
                  ),
                );
                void refreshSummary();
              }}
            />
            <IncidentManagerSummaryPanel
              summary={summary}
              loading={summaryLoading}
              error={summaryError}
            />
          </div>
        ) : (
          <div className="space-y-6">
            <IncidentUpload onFileSelected={handleAnalyze} disabled={analyzerLoading} />

            {analyzerLoading ? <LoadingState label="Analyzing file..." /> : null}

            {analyzerError ? (
              <ErrorState message={analyzerError} showHomeLink={false} />
            ) : null}

            {analyzerResult ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-stone-300">
                    Last analyzed file:{" "}
                    <span className="font-semibold text-amber-100">
                      {analyzerResult.sourcePath ?? "Unknown file"}
                    </span>
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      void handleDownload();
                    }}
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
                <IncidentSummary result={analyzerResult} />
              </>
            ) : null}
          </div>
        )}
      </div>
    </main>
  );
}
