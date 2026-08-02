"use client";

import { FormEvent, useMemo, useState } from "react";

import { askSupportAgent, resetSupportThreadId } from "@/lib/agent";
import {
  MEMORY_APPROVE_PHRASE,
  clearedMemoryMessage,
  getMemoryCoachingState,
  isBareAssent,
  type SupportTurn,
} from "@/lib/support-memory-coaching";

const EXAMPLE_QUESTIONS = [
  "Show me all incidents",
  "List open incidents at Miami Doral",
  "How many open incidents are there?",
  "Stock for beef at Chapinero",
  "How much beef do we have",
  "Current stock for SKU BEEF-001",
];

const SUPPORT_TIPS = [
  "Ask one topic per question — incidents, inventory, or knowledge base policy.",
  "Incidents: \"Show me all incidents\", \"List open incidents at Miami Doral\", or create/update with branch + details.",
  "Inventory reads only: use a product name (\"Stock for beef at Chapinero\"), SKU, or product ID — restock via the Inventory tab.",
  "Policies & loyalty: \"How many points for Gold tier?\" or \"How do I create an incident?\"",
  "Memory corrections: send the correction first, then reply in a separate message (e.g. \"Yes, please remember that\").",
];

export default function SupportPage(): React.JSX.Element {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<SupportTurn[]>([]);
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState("");
  const [tipsOpen, setTipsOpen] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState("");

  const inConversation = turns.length > 0;
  const memoryCoaching = useMemo(() => getMemoryCoachingState(turns), [turns]);
  const showBareAssentWarning =
    memoryCoaching?.kind === "awaiting_approval" && isBareAssent(question);

  const handleNewConversation = () => {
    resetSupportThreadId();
    setQuestion("");
    setTurns([]);
    setAskError("");
    setCopyFeedback("");
  };

  const handleUseApprovePhrase = () => {
    setQuestion(MEMORY_APPROVE_PHRASE);
    setAskError("");
    setCopyFeedback("");
  };

  const handleCopyApprovePhrase = async () => {
    try {
      await navigator.clipboard.writeText(MEMORY_APPROVE_PHRASE);
      setCopyFeedback("Copied");
    } catch {
      handleUseApprovePhrase();
      setCopyFeedback("Inserted into reply");
    }
  };

  const handleResendCorrection = () => {
    if (memoryCoaching?.kind !== "cleared" || !memoryCoaching.correctionToResend) {
      return;
    }
    setQuestion(memoryCoaching.correctionToResend);
    setAskError("");
    setCopyFeedback("");
  };

  const handleAsk = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setAskError("Enter a question before submitting.");
      return;
    }

    setAsking(true);
    setAskError("");
    setCopyFeedback("");
    try {
      const result = await askSupportAgent(trimmed);
      if (!result.answer?.trim()) {
        setAskError("The API returned an empty answer. Try again.");
        return;
      }
      setTurns((previous) => [
        ...previous,
        { question: trimmed, answer: result.answer },
      ]);
      setQuestion("");
    } catch (caught) {
      setAskError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setAsking(false);
    }
  };

  return (
    <main className="bo-page">
      <div className="bo-container-narrow space-y-6">
        <header className="bo-header">
          <p className="bo-eyebrow">Brasaland Support Agent</p>
          <h1 className="bo-title">Ask the traceable support agent</h1>
          <p className="bo-lead max-w-2xl">
            Live incidents and inventory stock via MCP and direct APIs, plus knowledge-base
            policies. Answers run through a LangGraph workflow with server-side tracing.
          </p>
        </header>

        <section className="bo-header">
          <button
            type="button"
            className="text-sm font-medium text-[color:var(--bo-accent)] hover:underline"
            onClick={() => setTipsOpen((open) => !open)}
            aria-expanded={tipsOpen}
          >
            {tipsOpen ? "Hide tips" : "Show example questions"}
          </button>
          {tipsOpen ? (
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm bo-muted">
              {SUPPORT_TIPS.map((tip) => (
                <li key={tip}>{tip}</li>
              ))}
            </ul>
          ) : null}

          <div className="mt-4 flex flex-wrap gap-2">
            {EXAMPLE_QUESTIONS.map((example) => (
              <button
                key={example}
                type="button"
                disabled={asking}
                className="rounded-full border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-panel-bg)] px-3 py-1.5 text-xs font-medium text-[color:var(--bo-fg)] transition hover:border-[color:var(--bo-accent)] hover:text-[color:var(--bo-accent)] disabled:opacity-50"
                onClick={() => {
                  setQuestion(example);
                  setAskError("");
                }}
              >
                {example}
              </button>
            ))}
          </div>

          {turns.length > 0 ? (
            <div className="mt-6 space-y-4" aria-live="polite">
              {turns.map((turn, index) => (
                <article
                  key={`${index}-${turn.question.slice(0, 24)}`}
                  className="space-y-3 rounded-xl border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-panel-bg)] p-4"
                >
                  <div className="space-y-1">
                    <h2 className="text-xs font-semibold uppercase tracking-[0.12em] bo-muted">
                      You asked
                    </h2>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-[color:var(--bo-fg)]">
                      {turn.question}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-xs font-semibold uppercase tracking-[0.12em] bo-muted">
                      Answer
                    </h3>
                    <div className="whitespace-pre-wrap rounded-lg border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-answer-bg)] px-3 py-2 text-sm leading-relaxed text-[color:var(--bo-fg)]">
                      {turn.answer}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : null}

          {memoryCoaching?.kind === "awaiting_approval" ? (
            <div
              className="mt-4 rounded-xl border border-[color:var(--bo-accent)] bg-[color:var(--bo-panel-bg)] p-4"
              role="status"
            >
              <p className="text-sm font-semibold text-[color:var(--bo-fg)]">
                Memory waiting for your confirmation
              </p>
              <p className="mt-2 text-sm leading-relaxed bo-muted">
                Reply in a separate message with explicit wording. Bare &quot;yes&quot; will not
                save it — use the suggested phrase below.
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  disabled={asking}
                  className="rounded-full border border-[color:var(--bo-accent)] bg-[color:var(--bo-panel-bg)] px-3 py-1.5 text-xs font-medium text-[color:var(--bo-accent)] transition hover:bg-[color:var(--bo-answer-bg)] disabled:opacity-50"
                  onClick={handleUseApprovePhrase}
                >
                  Use: {MEMORY_APPROVE_PHRASE}
                </button>
                <button
                  type="button"
                  disabled={asking}
                  className="rounded-full border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-panel-bg)] px-3 py-1.5 text-xs font-medium text-[color:var(--bo-fg)] transition hover:border-[color:var(--bo-accent)] hover:text-[color:var(--bo-accent)] disabled:opacity-50"
                  onClick={() => {
                    void handleCopyApprovePhrase();
                  }}
                >
                  Copy phrase
                </button>
                {copyFeedback ? (
                  <span className="text-xs bo-muted" aria-live="polite">
                    {copyFeedback}
                  </span>
                ) : null}
              </div>
            </div>
          ) : null}

          {memoryCoaching?.kind === "cleared" ? (
            <div className="bo-alert-error mt-4" role="status">
              <p className="font-semibold">Memory proposal cleared</p>
              <p className="mt-2 leading-relaxed">{clearedMemoryMessage(memoryCoaching.reason)}</p>
              {memoryCoaching.correctionToResend ? (
                <button
                  type="button"
                  disabled={asking}
                  className="bo-btn-secondary mt-3"
                  onClick={handleResendCorrection}
                >
                  Resend last correction
                </button>
              ) : null}
            </div>
          ) : null}

          <form onSubmit={handleAsk} className="mt-4 space-y-4">
            <label className="block space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] bo-muted">
                {inConversation ? "Reply" : "Question"}
              </span>
              <textarea
                value={question}
                onChange={(event) => {
                  setQuestion(event.target.value);
                  if (copyFeedback) {
                    setCopyFeedback("");
                  }
                }}
                rows={4}
                placeholder={
                  memoryCoaching?.kind === "awaiting_approval"
                    ? `Reply with "${MEMORY_APPROVE_PHRASE}" or ask a follow-up after approving`
                    : inConversation
                      ? `e.g. "${MEMORY_APPROVE_PHRASE}" or a follow-up question`
                      : 'e.g. "Show me all incidents" or "Stock for beef at Chapinero"'
                }
                className="bo-textarea"
                disabled={asking}
              />
            </label>

            {showBareAssentWarning ? (
              <p className="text-sm text-[color:var(--bo-error-fg)]" role="status">
                Bare &quot;yes&quot; won&apos;t confirm memory. Use &quot;{MEMORY_APPROVE_PHRASE}
                &quot; instead.
              </p>
            ) : null}

            <div className="flex flex-wrap gap-3">
              <button type="submit" disabled={asking} className="bo-btn-primary">
                {asking ? "Asking…" : "Ask"}
              </button>
              <button
                type="button"
                disabled={asking}
                className="bo-btn-secondary"
                onClick={handleNewConversation}
              >
                New conversation
              </button>
            </div>
          </form>

          {asking ? (
            <p className="mt-4 text-sm bo-muted" role="status">
              Running the support graph…
            </p>
          ) : null}

          {askError ? (
            <div className="bo-alert-error mt-4" role="alert">
              {askError}
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
