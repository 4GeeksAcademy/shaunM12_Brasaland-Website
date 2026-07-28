"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  fetchLatestPipelineRun,
  fetchWeeklyLocationPerformance,
  PipelineRunLatest,
  triggerPipelineRun,
  WeeklyLocationPerformanceRow,
} from "@/lib/reporting";
import { formatLocationLabel, getLocationById } from "@/lib/inventory-constants";

function formatMoney(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${value.toFixed(2)} ${currency}`;
  }
}

function formatRatio(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export default function ReportingPage(): React.JSX.Element {
  const [weekStart, setWeekStart] = useState<string>("");
  const [rows, setRows] = useState<WeeklyLocationPerformanceRow[]>([]);
  const [latestRun, setLatestRun] = useState<PipelineRunLatest | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string>("");
  const [message, setMessage] = useState<string>("");

  const load = useCallback(async (selectedWeek?: string) => {
    setLoading(true);
    setError("");
    try {
      const [kpiRows, run] = await Promise.all([
        fetchWeeklyLocationPerformance(selectedWeek || null),
        fetchLatestPipelineRun(),
      ]);
      setRows(kpiRows);
      setLatestRun(run);
      if (!selectedWeek && kpiRows[0]?.week_start) {
        setWeekStart(kpiRows[0].week_start);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const weekOptions = useMemo(() => {
    const fromRows = Array.from(new Set(rows.map((row) => row.week_start))).sort();
    if (weekStart && !fromRows.includes(weekStart)) {
      return [weekStart, ...fromRows];
    }
    if (latestRun?.week_start && !fromRows.includes(latestRun.week_start)) {
      return [latestRun.week_start, ...fromRows];
    }
    return fromRows;
  }, [latestRun?.week_start, rows, weekStart]);

  const handleWeekChange = async (next: string) => {
    setWeekStart(next);
    await load(next);
  };

  const handleRunPipeline = async () => {
    setRunning(true);
    setMessage("");
    setError("");
    try {
      const accepted = await triggerPipelineRun();
      setMessage(
        accepted.message
          ? `${accepted.message} (task_id: ${accepted.task_id})`
          : `Pipeline enqueued (task_id: ${accepted.task_id}).`,
      );
      // Poll a few times for completion without blocking the UI forever.
      for (let attempt = 0; attempt < 8; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        const run = await fetchLatestPipelineRun();
        setLatestRun(run);
        if (run && run.status !== "running") {
          break;
        }
      }
      await load(weekStart || undefined);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setRunning(false);
    }
  };

  return (
    <main className="bo-page">
      <div className="bo-container space-y-6">
        <header className="bo-header">
          <p className="bo-eyebrow">
            Brasaland Reporting
          </p>
          <h1 className="mt-2 bo-title">
            Weekly location performance
          </h1>
          <p className="mt-2 max-w-3xl text-sm bo-muted">
            Purchase cost, waste cost, waste ratio, stockouts, and price alerts by
            restaurant for Mariana and Felipe. Only locations with activity that week
            appear (sparse). COP and USD stay separate — no FX conversion.
          </p>
        </header>

        <section className="bo-section p-4 md:p-5">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <label className="flex flex-col gap-1 text-sm">
              <span className="uppercase tracking-[0.1em] text-[color:var(--bo-accent-muted)]/80">
                ISO week (Monday UTC)
              </span>
              <select
                className="rounded-lg border border-[color:var(--bo-card-border)] bg-[color:var(--bo-card)] px-3 py-2 text-[color:var(--bo-fg)]"
                value={weekStart}
                onChange={(event) => {
                  void handleWeekChange(event.target.value);
                }}
                disabled={loading || weekOptions.length === 0}
              >
                {weekOptions.length === 0 ? (
                  <option value="">No computed weeks yet</option>
                ) : (
                  weekOptions.map((week) => (
                    <option key={week} value={week}>
                      {week}
                    </option>
                  ))
                )}
              </select>
            </label>

            <button
              type="button"
              onClick={() => {
                void handleRunPipeline();
              }}
              disabled={running}
              className="bo-btn-secondary disabled:cursor-not-allowed"
            >
              {running ? "Running…" : "Run pipeline"}
            </button>
          </div>

          <div className="mt-4 grid gap-2 text-sm bo-muted md:grid-cols-2">
            <p>
              <span className="text-[color:var(--bo-accent-muted)]/80">Last run status:</span>{" "}
              {latestRun ? latestRun.status : "none yet"}
            </p>
            <p>
              <span className="text-[color:var(--bo-accent-muted)]/80">Extracted / loaded / skipped cost:</span>{" "}
              {latestRun
                ? `${latestRun.records_extracted} / ${latestRun.records_loaded} / ${latestRun.records_skipped_missing_cost}`
                : "—"}
            </p>
          </div>
          {message ? (
            <p className="mt-2 text-sm text-[color:var(--bo-success)]" role="status">
              {message}
            </p>
          ) : null}
          {error ? <p className="mt-2 text-sm text-[color:var(--bo-error-fg)]">{error}</p> : null}
        </section>

        <section className="overflow-x-auto bo-section">
          {loading ? (
            <p className="p-6 text-sm bo-muted">Loading weekly KPIs…</p>
          ) : rows.length === 0 ? (
            <p className="p-6 text-sm bo-muted">
              No locations with activity for this week. Run the pipeline after telemetry
              events exist, or pick another ISO week.
            </p>
          ) : (
            <table className="bo-table">
              <thead className="border-b border-[color:var(--bo-panel-border)] text-xs uppercase tracking-[0.1em] text-[color:var(--bo-accent-muted)]/80">
                <tr>
                  <th className="px-4 py-3">Location ID</th>
                  <th className="px-4 py-3">Location</th>
                  <th className="px-4 py-3">Country</th>
                  <th className="px-4 py-3">Currency</th>
                  <th className="px-4 py-3">Purchase Cost</th>
                  <th className="px-4 py-3">Waste Cost</th>
                  <th className="px-4 py-3">Waste Ratio</th>
                  <th className="px-4 py-3">Stockout Frequency</th>
                  <th className="px-4 py-3">Price Alert Frequency</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-[color:var(--bo-panel-border)] bo-fg-secondary last:border-0"
                  >
                    <td className="px-4 py-3 font-medium">{row.location_id}</td>
                    <td className="px-4 py-3">
                      {getLocationById(row.location_id)?.name ??
                        formatLocationLabel(row.location_id)}
                    </td>
                    <td className="px-4 py-3">{row.country}</td>
                    <td className="px-4 py-3">{row.currency}</td>
                    <td className="px-4 py-3">
                      {formatMoney(row.total_purchase_cost, row.currency)}
                    </td>
                    <td className="px-4 py-3">
                      {formatMoney(row.total_waste_cost, row.currency)}
                    </td>
                    <td className="px-4 py-3">{formatRatio(row.waste_ratio)}</td>
                    <td className="px-4 py-3">{row.stockout_events_count}</td>
                    <td className="px-4 py-3">{row.price_alert_events_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </main>
  );
}
