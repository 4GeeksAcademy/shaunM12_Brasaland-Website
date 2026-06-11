"use client";

import Link from "next/link";
import { useState } from "react";
import IncidentSummary from "@/components/incidents/IncidentSummary";
import IncidentUpload from "@/components/incidents/IncidentUpload";
import { analyzeIncidentFile, downloadIncidentResults } from "@/lib/incidents-api";
import { IncidentAnalysisResult } from "@/types/incidents";

export default function IncidentsPage(): React.JSX.Element {
  const [result, setResult] = useState<IncidentAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const handleAnalyze = async (file: File): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const analysis = await analyzeIncidentFile(file);
      setResult(analysis);
    } catch (caught) {
      setResult(null);
      setError(caught instanceof Error ? caught.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (): Promise<void> => {
    setDownloading(true);
    setError(null);
    try {
      const blob = await downloadIncidentResults();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "results.csv";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-stone-950 via-stone-900 to-amber-950 px-4 py-8 text-stone-100 md:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl border border-amber-200/15 bg-stone-950/95 p-6 shadow-2xl shadow-black/20">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm uppercase tracking-[0.12em] text-amber-300">Brasaland Incident Analyzer</p>
            <nav className="flex flex-wrap gap-2">
              <Link
                href="/"
                className="rounded-full border border-amber-300/70 px-4 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-amber-200 transition hover:bg-amber-300/10"
              >
                Candidate tracker
              </Link>
              <Link
                href="/data-processing"
                className="rounded-full border border-amber-300/70 px-4 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-amber-200 transition hover:bg-amber-300/10"
              >
                Data processing
              </Link>
            </nav>
          </div>
          <h1 className="mt-2 text-2xl font-extrabold text-amber-100 md:text-3xl">Incident File Analysis</h1>
          <p className="mt-2 max-w-3xl text-sm text-stone-300">
            Upload incident CSV files, validate records against context-5 rules, and review operational
            summaries for Brasaland locations.
          </p>
        </header>

        <IncidentUpload onFileSelected={handleAnalyze} disabled={loading} />

        {loading ? (
          <p className="rounded-xl border border-stone-700 bg-stone-900/80 px-4 py-3 text-sm text-stone-300">
            Analyzing file...
          </p>
        ) : null}

        {error ? (
          <p className="rounded-xl border border-rose-500/40 bg-rose-950/30 px-4 py-3 text-sm text-rose-100">
            {error}
          </p>
        ) : null}

        {result ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-stone-300">
                Last analyzed file: <span className="font-semibold text-amber-100">{result.sourcePath}</span>
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
            <IncidentSummary result={result} />
          </>
        ) : null}
      </div>
    </main>
  );
}
