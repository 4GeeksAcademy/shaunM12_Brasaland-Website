import { IncidentAnalysisResult } from "@/types/incidents";

const INVALID_RULE_ORDER = [
  "Missing location_id",
  "Invalid or missing category",
  "Empty description",
  "Missing reporter_id",
  "Closed case, no score",
  "Out-of-range satisfaction_score",
] as const;

const SATISFACTION_LABELS: Record<number, string> = {
  1: "Very dissatisfied",
  2: "Dissatisfied",
  3: "Neutral",
  4: "Satisfied",
  5: "Very satisfied",
};

function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatPercentage(count: number, total: number): string {
  if (total <= 0) {
    return "0.0%";
  }
  return `${((count / total) * 100).toFixed(1)}%`;
}

function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string;
}): React.JSX.Element {
  return (
    <article className="rounded-xl border border-amber-500/30 bg-amber-900/20 p-4">
      <p className="text-xs uppercase tracking-[0.12em] text-amber-200">{label}</p>
      <p className="mt-1 text-3xl font-extrabold text-amber-100">{value}</p>
      {detail ? <p className="text-xs text-amber-200/80">{detail}</p> : null}
    </article>
  );
}

function BreakdownList({
  title,
  rows,
  total,
}: {
  title: string;
  rows: Array<{ label: string; value: number }>;
  total: number;
}): React.JSX.Element {
  return (
    <article className="rounded-2xl border border-amber-200/20 bg-stone-950/70 p-5 shadow-xl shadow-black/20">
      <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-amber-300">{title}</h3>
      <ul className="mt-4 space-y-2">
        {rows.map((row) => (
          <li
            key={row.label}
            className="flex items-center justify-between rounded-lg border border-stone-700/60 bg-stone-900/80 px-3 py-2 text-sm"
          >
            <span className="text-stone-200">{row.label}</span>
            <span className="font-semibold text-amber-200">
              {formatNumber(row.value)}{" "}
              <span className="text-xs font-normal text-stone-400">
                ({formatPercentage(row.value, total)})
              </span>
            </span>
          </li>
        ))}
      </ul>
    </article>
  );
}

export default function IncidentSummary({
  result,
}: {
  result: IncidentAnalysisResult;
}): React.JSX.Element {
  const categoryRows = Object.entries(result.byCategory).map(([label, value]) => ({
    label,
    value,
  }));
  const statusRows = Object.entries(result.byStatus).map(([label, value]) => ({
    label,
    value,
  }));

  const invalidRows = INVALID_RULE_ORDER.filter((label) => (result.invalidReasons[label] ?? 0) > 0).map(
    (label) => [label, result.invalidReasons[label]] as const,
  );

  const satisfactionRows = [1, 2, 3, 4, 5].map((score) => ({
    label: `Score ${score} (${SATISFACTION_LABELS[score]})`,
    value: result.satisfactionScoreBreakdown[String(score)] ?? 0,
  }));

  return (
    <div className="space-y-6">
      {result.schemaError ? (
        <section className="rounded-2xl border border-rose-500/40 bg-rose-950/30 p-5">
          <h2 className="text-lg font-bold text-rose-200">Schema error</h2>
          <p className="mt-2 text-sm text-rose-100">{result.schemaError}</p>
        </section>
      ) : null}

      <section className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Total records in file" value={formatNumber(result.totalProcessed)} />
        <MetricCard label="Valid records" value={formatNumber(result.validCount)} />
        <MetricCard label="Invalid / incomplete" value={formatNumber(result.invalidCount)} />
        <MetricCard
          label="Avg satisfaction"
          value={result.avgSatisfactionClosed !== null ? result.avgSatisfactionClosed.toFixed(2) : "N/A"}
          detail={
            result.closedCaseCount > 0
              ? `Scored cases: ${result.satisfactionClosedCount} of ${result.closedCaseCount}`
              : "No closed cases"
          }
        />
      </section>

      {result.invalidCount > 0 ? (
        <section className="rounded-2xl border border-rose-500/30 bg-rose-950/20 p-5">
          <h2 className="text-lg font-bold text-rose-200">Invalid records breakdown</h2>
          <p className="mt-1 text-sm text-rose-100/90">
            The uploaded file contains {formatNumber(result.invalidCount)} invalid or incomplete record
            {result.invalidCount === 1 ? "" : "s"}.
          </p>
          <ul className="mt-4 space-y-2">
            {invalidRows.map(([reason, count]) => (
              <li
                key={reason}
                className="flex items-center justify-between rounded-lg border border-rose-800/50 bg-stone-950/70 px-3 py-2 text-sm"
              >
                <span className="text-rose-100">{reason}</span>
                <span className="font-semibold text-rose-200">{formatNumber(count)}</span>
              </li>
            ))}
          </ul>
          {result.invalidRowSamples.length > 0 ? (
            <p className="mt-3 text-xs text-rose-200/80">
              Sample CSV rows: {result.invalidRowSamples.slice(0, 10).join(", ")}
              {result.invalidRowSamples.length > 10 ? ", ..." : ""}
            </p>
          ) : null}
        </section>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <BreakdownList
          title="Breakdown by category (valid records)"
          rows={categoryRows}
          total={result.validCount}
        />
        <BreakdownList
          title="Breakdown by status (valid records)"
          rows={statusRows}
          total={result.validCount}
        />
      </section>

      <section className="rounded-2xl border border-amber-200/20 bg-stone-950/70 p-5 shadow-xl shadow-black/20">
        <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-amber-300">
          Satisfaction index (closed cases)
        </h3>
        <p className="mt-2 text-sm text-stone-300">
          Scored cases: {formatNumber(result.satisfactionClosedCount)} of{" "}
          {formatNumber(result.closedCaseCount)}
          {result.avgSatisfactionClosed !== null
            ? ` · Average score: ${result.avgSatisfactionClosed.toFixed(2)} / 5.00`
            : null}
        </p>
        <ul className="mt-4 space-y-2">
          {satisfactionRows.map((row) => (
            <li
              key={row.label}
              className="flex items-center justify-between rounded-lg border border-stone-700/60 bg-stone-900/80 px-3 py-2 text-sm"
            >
              <span className="text-stone-200">{row.label}</span>
              <span className="font-semibold text-amber-200">{formatNumber(row.value)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
