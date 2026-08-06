"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import {
  getRfpTicket,
  isRfpTerminalStatus,
  RFP_STATUS_ANALYZING,
  RfpTicketDetail,
} from "@/lib/rfp";

const POLL_INTERVAL_MS = 2500;

function formatStatus(status: string): string {
  return status.replaceAll("_", " ");
}

function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case "intake_complete":
      return "border-[color:var(--bo-success)]/40 bg-[color:var(--bo-success)]/10 text-[color:var(--bo-success)]";
    case "discarded":
      return "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300";
    case "failed":
      return "border-[color:var(--bo-error-fg)]/40 bg-[color:var(--bo-error-fg)]/10 text-[color:var(--bo-error-fg)]";
    case "analyzing":
      return "border-[color:var(--bo-accent)]/40 bg-[color:var(--bo-accent-soft)] text-[color:var(--bo-accent)]";
    default:
      return "border-[color:var(--bo-panel-border)] bg-[color:var(--bo-row-bg)] bo-muted";
  }
}

function formatMetadataLabel(key: string): string {
  return key.replaceAll("_", " ");
}

function isScalarMetadataValue(value: unknown): value is string | number | boolean {
  return (
    typeof value === "string" || typeof value === "number" || typeof value === "boolean"
  );
}

const READABILITY_LABELS: Record<string, string> = {
  flesch_kincaid_grade: "Flesch-Kincaid grade",
  flesch_reading_ease: "Flesch reading ease",
  gunning_fog: "Gunning Fog",
};

function ReadabilityScores({ scores }: { scores: Record<string, unknown> }): React.JSX.Element {
  return (
    <dl className="mt-1 grid gap-3 sm:grid-cols-3">
      {Object.entries(scores).map(([key, value]) => (
        <div key={key}>
          <dt className="text-xs bo-muted">{READABILITY_LABELS[key] ?? formatMetadataLabel(key)}</dt>
          <dd className="mt-0.5 font-mono text-sm tabular-nums text-[color:var(--bo-fg)]">
            {typeof value === "number" ? value.toFixed(1) : String(value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function MetadataValue({
  fieldKey,
  value,
}: {
  fieldKey: string;
  value: unknown;
}): React.JSX.Element {
  if (
    fieldKey === "readability_scores" &&
    value &&
    typeof value === "object" &&
    !Array.isArray(value)
  ) {
    return <ReadabilityScores scores={value as Record<string, unknown>} />;
  }

  if (isScalarMetadataValue(value)) {
    return <span className="break-words">{String(value)}</span>;
  }

  if (value && typeof value === "object") {
    return (
      <pre className="mt-1 max-w-full overflow-x-auto whitespace-pre-wrap break-words rounded-lg border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-row-bg)] p-2 font-mono text-xs leading-relaxed text-[color:var(--bo-fg)]">
        {JSON.stringify(value, null, 2)}
      </pre>
    );
  }

  return <span className="break-words">{String(value)}</span>;
}

function metadataGridSpanClass(fieldKey: string, value: unknown): string {
  if (fieldKey === "readability_scores") {
    return "md:col-span-2";
  }
  if (value && typeof value === "object" && !isScalarMetadataValue(value)) {
    return "md:col-span-2";
  }
  return "";
}

function sortMetadataEntries(entries: [string, unknown][]): [string, unknown][] {
  return [...entries].sort(([keyA], [keyB]) => {
    if (keyA === "readability_scores") {
      return 1;
    }
    if (keyB === "readability_scores") {
      return -1;
    }
    return keyA.localeCompare(keyB);
  });
}

function MetadataGrid({ metadata }: { metadata: Record<string, unknown> }): React.JSX.Element {
  const entries = sortMetadataEntries(Object.entries(metadata));
  if (!entries.length) {
    return <p className="text-sm bo-muted">No metadata extracted.</p>;
  }
  return (
    <dl className="grid gap-4 text-sm md:grid-cols-2">
      {entries.map(([key, value]) => (
        <div key={key} className={metadataGridSpanClass(key, value)}>
          <dt className="text-xs uppercase tracking-[0.12em] bo-muted">
            {formatMetadataLabel(key)}
          </dt>
          <dd className="mt-1 min-w-0 text-[color:var(--bo-fg)]">
            <MetadataValue fieldKey={key} value={value} />
          </dd>
        </div>
      ))}
    </dl>
  );
}

export default function RfpDetailPage(): React.JSX.Element {
  const params = useParams<{ id: string }>();
  const ticketId = params.id;

  const [ticket, setTicket] = useState<RfpTicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);

  const loadTicket = useCallback(async (): Promise<RfpTicketDetail | null> => {
    if (!ticketId) {
      setError("Missing ticket id.");
      setLoading(false);
      return null;
    }

    setError(null);
    try {
      const detail = await getRfpTicket(ticketId);
      setTicket(detail);
      return detail;
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Failed to load RFP ticket.",
      );
      setTicket(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    setLoading(true);
    void loadTicket();
  }, [loadTicket]);

  useEffect(() => {
    if (!ticket || isRfpTerminalStatus(ticket.status)) {
      setPolling(false);
      return undefined;
    }

    setPolling(true);
    const intervalId = window.setInterval(() => {
      void loadTicket();
    }, POLL_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
      setPolling(false);
    };
  }, [ticket?.status, loadTicket]);

  return (
    <main className="bo-page">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="bo-header">
          <Link
            href="/rfp"
            className="text-sm font-semibold text-[color:var(--bo-accent)] transition hover:text-[color:var(--bo-accent-muted)]"
          >
            ← Back to RFP tickets
          </Link>
          <p className="mt-4 bo-eyebrow">RFP Intake</p>
          <h1 className="mt-1 bo-title">Ticket detail</h1>
          {ticket ? (
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <span
                className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] ${statusBadgeClass(ticket.status)}`}
              >
                {ticket.status_label || formatStatus(ticket.status)}
              </span>
              {polling || ticket.status === RFP_STATUS_ANALYZING ? (
                <span className="text-xs bo-muted" role="status">
                  Polling for completion…
                </span>
              ) : null}
              <span className="font-mono text-xs bo-muted">{ticket.ticket_id}</span>
            </div>
          ) : null}
        </header>

        {loading && !ticket ? <LoadingState label="Loading ticket…" /> : null}

        {error ? (
          <ErrorState
            message={error}
            onRetry={() => {
              setLoading(true);
              void loadTicket();
            }}
            showHomeLink={false}
          />
        ) : null}

        {ticket ? (
          <div className="space-y-6">
            {ticket.status === "discarded" && ticket.discard_reason ? (
              <section className="bo-alert-error" role="alert">
                Discarded: {ticket.discard_reason}
              </section>
            ) : null}

            {ticket.status === "failed" && (ticket.error_message || ticket.error_code) ? (
              <section className="bo-alert-error" role="alert">
                {ticket.error_message ?? "Intake failed."}
                {ticket.error_code ? ` (${ticket.error_code})` : ""}
              </section>
            ) : null}

            <section className="bo-card-lg space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-[0.12em] bo-muted">
                Overview
              </h2>
              <dl className="grid gap-4 text-sm md:grid-cols-2">
                <div>
                  <dt className="text-xs uppercase tracking-[0.12em] bo-muted">CEO approval</dt>
                  <dd className="mt-1 font-semibold text-[color:var(--bo-fg)]">
                    {ticket.requires_ceo_approval ? "Required (> $50k USD/year)" : "Not required"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.12em] bo-muted">Markdown</dt>
                  <dd className="mt-1 text-[color:var(--bo-fg)]">
                    {ticket.has_markdown
                      ? `${ticket.markdown_length.toLocaleString()} characters`
                      : "Not available"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.12em] bo-muted">Departments</dt>
                  <dd className="mt-1 text-[color:var(--bo-fg)]">
                    {ticket.departments_needed.length
                      ? ticket.departments_needed.join(", ")
                      : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.12em] bo-muted">Created</dt>
                  <dd className="mt-1 text-[color:var(--bo-fg)]">
                    {formatTimestamp(ticket.created_at)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.12em] bo-muted">Updated</dt>
                  <dd className="mt-1 text-[color:var(--bo-fg)]">
                    {formatTimestamp(ticket.updated_at)}
                  </dd>
                </div>
              </dl>
            </section>

            {ticket.intake_summary ? (
              <section className="bo-card-lg space-y-3">
                <h2 className="text-sm font-semibold uppercase tracking-[0.12em] bo-muted">
                  Intake summary
                </h2>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-[color:var(--bo-fg)]">
                  {ticket.intake_summary}
                </p>
              </section>
            ) : null}

            <section className="bo-card-lg space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-[0.12em] bo-muted">
                Metadata
              </h2>
              <MetadataGrid metadata={ticket.metadata} />
            </section>

            {ticket.sections.length > 0 ? (
              <section className="bo-card-lg space-y-4">
                <h2 className="text-sm font-semibold uppercase tracking-[0.12em] bo-muted">
                  Department routing
                </h2>
                <div className="space-y-4">
                  {ticket.sections.map((section) => (
                    <article
                      key={section.department_id}
                      className="rounded-xl border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-row-bg)] p-4"
                    >
                      <h3 className="text-sm font-semibold text-[color:var(--bo-heading)]">
                        {section.department_label ||
                          section.department_id.replaceAll("_", " ")}
                      </h3>
                      <p className="mt-1 text-xs bo-muted">
                        Approach:{" "}
                        <span className="font-semibold text-[color:var(--bo-fg)]">
                          {section.department_owner}
                        </span>
                      </p>
                      {section.key_aspects.length ? (
                        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-[color:var(--bo-fg)]">
                          {section.key_aspects.map((aspect) => (
                            <li key={aspect}>{aspect}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-2 text-sm bo-muted">No key aspects recorded.</p>
                      )}
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            {ticket.unmapped_topics.length > 0 ? (
              <section className="bo-card-lg space-y-3">
                <h2 className="text-sm font-semibold uppercase tracking-[0.12em] bo-muted">
                  Unmapped topics
                </h2>
                <ul className="list-disc space-y-1 pl-5 text-sm text-[color:var(--bo-fg)]">
                  {ticket.unmapped_topics.map((topic) => (
                    <li key={topic}>{topic}</li>
                  ))}
                </ul>
              </section>
            ) : null}

            {ticket.conflicts.length > 0 ? (
              <section className="bo-card-lg space-y-3">
                <h2 className="text-sm font-semibold uppercase tracking-[0.12em] bo-muted">
                  Conflicts
                </h2>
                <ul className="space-y-2 text-sm text-[color:var(--bo-fg)]">
                  {ticket.conflicts.map((conflict, index) => (
                    <li
                      key={`${index}-${JSON.stringify(conflict)}`}
                      className="rounded-lg border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-row-bg)] px-3 py-2"
                    >
                      {typeof conflict.message === "string"
                        ? conflict.message
                        : JSON.stringify(conflict)}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
          </div>
        ) : null}
      </div>
    </main>
  );
}
