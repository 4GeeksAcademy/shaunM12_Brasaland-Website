"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import {
  countTerminalDraftSections,
  deleteRfpTicket,
  getRfpTicket,
  isGenerationInProgress,
  RFP_DRAFT_STATUS_NEEDS_HUMAN_REVIEW,
  RFP_DRAFT_STATUS_PASSED,
  RFP_STATUS_ANALYZING,
  RFP_STATUS_DRAFTING,
  RFP_STATUS_INTAKE_COMPLETE,
  RFP_STATUS_UNDER_EVALUATION,
  RFP_STATUS_WAITING_FOR_APPROVAL,
  RfpSection,
  RfpTicketDetail,
  shouldPollRfpTicketDetail,
  startRfpDraft,
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
    case RFP_STATUS_INTAKE_COMPLETE:
      return "border-[color:var(--bo-success)]/40 bg-[color:var(--bo-success)]/10 text-[color:var(--bo-success)]";
    case RFP_STATUS_WAITING_FOR_APPROVAL:
      return "border-violet-500/40 bg-violet-500/10 text-violet-700 dark:text-violet-300";
    case "completed":
      return "border-[color:var(--bo-success)]/40 bg-[color:var(--bo-success)]/10 text-[color:var(--bo-success)]";
    case RFP_STATUS_DRAFTING:
    case RFP_STATUS_UNDER_EVALUATION:
      return "border-[color:var(--bo-accent)]/40 bg-[color:var(--bo-accent-soft)] text-[color:var(--bo-accent)]";
    case "discarded":
      return "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300";
    case "failed":
      return "border-[color:var(--bo-error-fg)]/40 bg-[color:var(--bo-error-fg)]/10 text-[color:var(--bo-error-fg)]";
    case RFP_STATUS_ANALYZING:
      return "border-[color:var(--bo-accent)]/40 bg-[color:var(--bo-accent-soft)] text-[color:var(--bo-accent)]";
    default:
      return "border-[color:var(--bo-panel-border)] bg-[color:var(--bo-row-bg)] bo-muted";
  }
}

function draftStatusBadgeClass(draftStatus: string): string {
  switch (draftStatus) {
    case RFP_DRAFT_STATUS_PASSED:
      return "border-[color:var(--bo-success)]/40 bg-[color:var(--bo-success)]/10 text-[color:var(--bo-success)]";
    case RFP_DRAFT_STATUS_NEEDS_HUMAN_REVIEW:
      return "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300";
    case "drafting":
    case "evaluating":
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

interface EvaluationDimension {
  passed?: boolean;
  missing_topics?: string[];
  failures?: Array<{ rule_id?: string; message?: string; suggested_fix?: string }>;
  advisory?: Array<{ rule_id?: string; message?: string; suggested_fix?: string }>;
  flesch_kincaid_grade?: number | null;
  note?: string;
}

interface EvaluationRun {
  iteration?: number;
  overall_passed?: boolean;
  needs_human_review?: boolean;
  readability?: EvaluationDimension;
  relevance?: EvaluationDimension;
  compliance?: EvaluationDimension;
}

function isEvaluationRun(value: unknown): value is EvaluationRun {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function passFailLabel(passed: boolean | undefined): string {
  if (passed === undefined) {
    return "—";
  }
  return passed ? "Pass" : "Fail";
}

function passFailClass(passed: boolean | undefined): string {
  if (passed === undefined) {
    return "bo-muted";
  }
  return passed
    ? "text-[color:var(--bo-success)]"
    : "text-[color:var(--bo-error-fg)]";
}

function complianceBlockingFailures(
  compliance: EvaluationDimension | undefined,
): Array<{ rule_id?: string; message?: string; suggested_fix?: string }> {
  const failures = compliance?.failures ?? [];
  const advisory = compliance?.advisory ?? [];
  if (advisory.length > 0) {
    return failures;
  }
  return failures.filter((failure) => failure.rule_id !== "COMPLIANCE_CEO_THRESHOLD_50K");
}

function complianceAdvisoryFlags(
  compliance: EvaluationDimension | undefined,
): Array<{ rule_id?: string; message?: string; suggested_fix?: string }> {
  const advisory = compliance?.advisory ?? [];
  if (advisory.length > 0) {
    return advisory;
  }
  return (compliance?.failures ?? []).filter(
    (failure) => failure.rule_id === "COMPLIANCE_CEO_THRESHOLD_50K",
  );
}

function EvaluationRunCard({
  evaluation,
  title,
}: {
  evaluation: EvaluationRun;
  title: string;
}): React.JSX.Element {
  const iteration = evaluation.iteration ?? 1;
  const overallPassed = evaluation.overall_passed === true;
  const blockingFailures = complianceBlockingFailures(evaluation.compliance);
  const advisoryFlags = complianceAdvisoryFlags(evaluation.compliance);

  return (
    <div className="rounded-lg border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-row-bg)] p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-xs font-semibold uppercase tracking-[0.12em] bo-muted">{title}</h4>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs bo-muted">Iteration {iteration}</span>
          <span
            className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold uppercase tracking-[0.08em] ${
              overallPassed
                ? "border-[color:var(--bo-success)]/40 bg-[color:var(--bo-success)]/10 text-[color:var(--bo-success)]"
                : "border-[color:var(--bo-error-fg)]/40 bg-[color:var(--bo-error-fg)]/10 text-[color:var(--bo-error-fg)]"
            }`}
          >
            {overallPassed ? "Passed" : "Failed"}
          </span>
          {evaluation.needs_human_review ? (
            <span className="inline-flex rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-xs font-semibold uppercase tracking-[0.08em] text-amber-700 dark:text-amber-300">
              Needs human review
            </span>
          ) : null}
        </div>
      </div>
      <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs bo-muted">Readability</dt>
          <dd className={`mt-0.5 font-semibold ${passFailClass(evaluation.readability?.passed)}`}>
            {passFailLabel(evaluation.readability?.passed)}
            {evaluation.readability?.flesch_kincaid_grade != null ? (
              <span className="ml-1 font-normal bo-muted">
                (FK {evaluation.readability.flesch_kincaid_grade})
              </span>
            ) : null}
          </dd>
          {evaluation.readability?.note ? (
            <p className="mt-1 text-xs bo-muted">{evaluation.readability.note}</p>
          ) : null}
        </div>
        <div>
          <dt className="text-xs bo-muted">Relevance</dt>
          <dd className={`mt-0.5 font-semibold ${passFailClass(evaluation.relevance?.passed)}`}>
            {passFailLabel(evaluation.relevance?.passed)}
          </dd>
          {evaluation.relevance?.missing_topics?.length ? (
            <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs bo-muted">
              {evaluation.relevance.missing_topics.map((topic) => (
                <li key={topic}>{topic}</li>
              ))}
            </ul>
          ) : null}
        </div>
        <div>
          <dt className="text-xs bo-muted">Compliance</dt>
          <dd className={`mt-0.5 font-semibold ${passFailClass(evaluation.compliance?.passed)}`}>
            {passFailLabel(evaluation.compliance?.passed)}
          </dd>
          {blockingFailures.length ? (
            <ul className="mt-1 space-y-1 text-xs">
              {blockingFailures.map((failure, index) => (
                <li key={`${failure.rule_id ?? index}-${index}`} className="bo-muted">
                  <span className="font-mono text-[color:var(--bo-fg)]">
                    {failure.rule_id ?? "RULE"}
                  </span>
                  {failure.message ? `: ${failure.message}` : ""}
                </li>
              ))}
            </ul>
          ) : null}
          {advisoryFlags.length ? (
            <div className="mt-2">
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-amber-700 dark:text-amber-300">
                Advisory
              </p>
              <ul className="mt-1 space-y-1 text-xs">
                {advisoryFlags.map((flag, index) => (
                  <li
                    key={`${flag.rule_id ?? index}-advisory-${index}`}
                    className="text-amber-800/90 dark:text-amber-200/90"
                  >
                    <span className="font-mono">{flag.rule_id ?? "ADVISORY"}</span>
                    {flag.message ? `: ${flag.message}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </dl>
    </div>
  );
}

function SectionEvaluationPanel({
  evaluationResults,
}: {
  evaluationResults: Record<string, unknown> | null | undefined;
}): React.JSX.Element | null {
  if (!evaluationResults || typeof evaluationResults !== "object") {
    return null;
  }

  const latest = evaluationResults.latest;
  const historyRaw = evaluationResults.history;
  const history = Array.isArray(historyRaw)
    ? historyRaw.filter(isEvaluationRun)
    : [];

  if (!isEvaluationRun(latest)) {
    return null;
  }

  return (
    <div className="mt-4 space-y-3">
      <h4 className="text-xs font-semibold uppercase tracking-[0.12em] bo-muted">
        Evaluation
      </h4>
      <EvaluationRunCard evaluation={latest} title="Latest" />
      {history.length > 0 ? (
        <details className="group">
          <summary className="cursor-pointer text-xs font-semibold text-[color:var(--bo-accent)] hover:underline">
            {history.length} prior iteration{history.length === 1 ? "" : "s"}
          </summary>
          <div className="mt-2 space-y-2">
            {[...history].reverse().map((run, index) => (
              <EvaluationRunCard
                key={`history-${run.iteration ?? index}-${index}`}
                evaluation={run}
                title={`Iteration ${run.iteration ?? index + 1}`}
              />
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}

function DepartmentSectionCard({
  section,
}: {
  section: RfpSection;
}): React.JSX.Element {
  const hasDraft = Boolean(section.draft_content?.trim());

  return (
    <article className="rounded-xl border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-row-bg)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-[color:var(--bo-heading)]">
            {section.department_label || section.department_id.replaceAll("_", " ")}
          </h3>
          <p className="mt-1 text-xs bo-muted">
            Approach:{" "}
            <span className="font-semibold text-[color:var(--bo-fg)]">
              {section.department_owner}
            </span>
          </p>
        </div>
        <span
          className={`inline-flex shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-[0.08em] ${draftStatusBadgeClass(section.draft_status)}`}
        >
          {section.draft_status_label || formatStatus(section.draft_status)}
        </span>
      </div>

      {section.key_aspects.length ? (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-[color:var(--bo-fg)]">
          {section.key_aspects.map((aspect) => (
            <li key={aspect}>{aspect}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm bo-muted">No key aspects recorded.</p>
      )}

      {hasDraft ? (
        <div className="mt-4 space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-[0.12em] bo-muted">
            Draft response
          </h4>
          <div className="max-h-96 overflow-y-auto rounded-lg border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-panel-bg)] p-3">
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-[color:var(--bo-fg)]">
              {section.draft_content}
            </p>
          </div>
        </div>
      ) : null}

      <SectionEvaluationPanel evaluationResults={section.evaluation_results} />
    </article>
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
  const router = useRouter();
  const ticketId = params.id;

  const [ticket, setTicket] = useState<RfpTicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const [draftStarting, setDraftStarting] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

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
    if (!ticket || !shouldPollRfpTicketDetail(ticket)) {
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
  }, [ticket, loadTicket]);

  const handleStartDraft = async (): Promise<void> => {
    if (!ticketId || !ticket || ticket.status !== RFP_STATUS_INTAKE_COMPLETE) {
      return;
    }

    setDraftStarting(true);
    setDraftError(null);
    try {
      const started = await startRfpDraft(ticketId);
      setTicket((current) =>
        current
          ? {
              ...current,
              status: started.status,
              status_label: started.status_label,
            }
          : current,
      );
      void loadTicket();
    } catch (caught) {
      setDraftError(
        caught instanceof Error ? caught.message : "Could not start drafting.",
      );
    } finally {
      setDraftStarting(false);
    }
  };

  const draftProgress = ticket
    ? countTerminalDraftSections(ticket.sections)
    : { completed: 0, total: 0 };
  const generationInProgress = ticket ? isGenerationInProgress(ticket) : false;

  const handleDeleteTicket = async (): Promise<void> => {
    if (!ticketId) {
      return;
    }
    const confirmed = window.confirm(
      "Delete this RFP ticket permanently?\n\nThis removes all sections, evaluations, and the stored PDF.",
    );
    if (!confirmed) {
      return;
    }

    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteRfpTicket(ticketId);
      router.push("/rfp");
    } catch (caught) {
      setDeleteError(
        caught instanceof Error ? caught.message : "Could not delete ticket.",
      );
    } finally {
      setDeleting(false);
    }
  };

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
          <p className="mt-4 bo-eyebrow">RFP workflow</p>
          <h1 className="mt-1 bo-title">Ticket detail</h1>
          {ticket ? (
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <span
                className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] ${statusBadgeClass(ticket.status)}`}
              >
                {ticket.status_label || formatStatus(ticket.status)}
              </span>
              {polling ? (
                <span className="text-xs bo-muted" role="status">
                  {ticket.status === RFP_STATUS_ANALYZING
                    ? "Polling for intake completion…"
                    : generationInProgress && draftProgress.total > 0
                      ? `Generating department drafts (${draftProgress.completed}/${draftProgress.total} complete)…`
                      : ticket.status === RFP_STATUS_DRAFTING
                        ? "Generating department drafts…"
                        : ticket.status === RFP_STATUS_UNDER_EVALUATION
                          ? "Running evaluations…"
                          : "Updating…"}
                </span>
              ) : null}
              <span className="font-mono text-xs bo-muted">{ticket.ticket_id}</span>
              <button
                type="button"
                disabled={deleting}
                onClick={() => void handleDeleteTicket()}
                className="rounded-lg border border-[color:var(--bo-error-fg)]/40 px-3 py-1 text-xs font-semibold text-[color:var(--bo-error-fg)] disabled:opacity-50"
              >
                {deleting ? "Deleting…" : "Delete ticket"}
              </button>
            </div>
          ) : null}
        </header>

        {deleteError ? (
          <div className="bo-alert-error" role="alert">
            {deleteError}
          </div>
        ) : null}

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

            {ticket.status === RFP_STATUS_INTAKE_COMPLETE ? (
              <section className="bo-card-lg space-y-3">
                <h2 className="text-sm font-semibold uppercase tracking-[0.12em] bo-muted">
                  Response generation
                </h2>
                <p className="text-sm bo-muted">
                  Intake is complete. Start drafting to generate per-department responses
                  and run readability, relevance, and compliance evaluations.
                </p>
                <button
                  type="button"
                  disabled={draftStarting}
                  onClick={() => void handleStartDraft()}
                  className="bo-btn-primary px-4 py-2 text-sm normal-case tracking-normal disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {draftStarting ? "Starting…" : "Start drafting"}
                </button>
                {draftError ? (
                  <div className="bo-alert-error" role="alert">
                    {draftError}
                  </div>
                ) : null}
              </section>
            ) : null}

            {generationInProgress ? (
              <section className="bo-card-lg space-y-2" role="status">
                <h2 className="text-sm font-semibold uppercase tracking-[0.12em] bo-muted">
                  Generation in progress
                </h2>
                <p className="text-sm bo-muted">
                  {draftProgress.total > 0
                    ? `${draftProgress.completed} of ${draftProgress.total} department sections finished. Sections update as each completes — this can take several minutes with a live LLM.`
                    : "Department drafts are generating in the background. This can take several minutes with a live LLM."}
                </p>
              </section>
            ) : null}

            {ticket.status === RFP_STATUS_WAITING_FOR_APPROVAL &&
            !generationInProgress ? (
              <section className="bo-card-lg space-y-2">
                <h2 className="text-sm font-semibold uppercase tracking-[0.12em] bo-muted">
                  Ready for review
                </h2>
                <p className="text-sm bo-muted">
                  All department drafts finished evaluation. Human approval and final
                  document merge are handled in a later milestone (Part 3).
                </p>
              </section>
            ) : null}

            {ticket.status === "failed" && (ticket.error_message || ticket.error_code) ? (
              <section className="bo-alert-error" role="alert">
                {ticket.error_message ?? "Workflow failed."}
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
                  Department sections
                </h2>
                <div className="space-y-4">
                  {ticket.sections.map((section) => (
                    <DepartmentSectionCard
                      key={section.department_id}
                      section={section}
                    />
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
