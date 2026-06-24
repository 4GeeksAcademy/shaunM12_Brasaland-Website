"use client";

import { useState } from "react";
import IncidentSummary from "@/components/incidents/IncidentSummary";
import IncidentUpload from "@/components/incidents/IncidentUpload";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import { useApiState } from "@/hooks/useApiState";
import { analyzeIncidentFile, downloadIncidentResults } from "@/lib/incidents-api";
import { IncidentAnalysisResult } from "@/types/incidents";

export default function IncidentsPage(): React.JSX.Element {
  const {
    data: result,
    state,
    error,
    execute,
  } = useApiState<IncidentAnalysisResult>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

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

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-8 text-stone-100 md:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20">
          <p className="text-sm uppercase tracking-[0.12em] text-amber-300">Brasaland Incident Analyzer</p>
          <h1 className="mt-2 text-2xl font-extrabold text-amber-100 md:text-3xl">Incident File Analysis</h1>
          <p className="mt-2 max-w-3xl text-sm text-stone-300">
            Upload incident CSV files, validate records against context-5 rules, and review operational
            summaries for Brasaland locations.
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
      </div>
    </main>
  );
}
