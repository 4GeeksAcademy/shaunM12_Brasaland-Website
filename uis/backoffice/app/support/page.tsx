"use client";

import { FormEvent, useState } from "react";

import { askSupportAgent } from "@/lib/agent";

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
];

export default function SupportPage(): React.JSX.Element {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState("");
  const [tipsOpen, setTipsOpen] = useState(false);

  const handleAsk = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setAskError("Enter a question before submitting.");
      setAnswer(null);
      return;
    }

    setAsking(true);
    setAskError("");
    setAnswer(null);
    try {
      const result = await askSupportAgent(trimmed);
      if (!result.answer?.trim()) {
        setAskError("The API returned an empty answer. Try again.");
        return;
      }
      setAnswer(result.answer);
    } catch (caught) {
      setAskError(caught instanceof Error ? caught.message : String(caught));
      setAnswer(null);
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
                  setAnswer(null);
                }}
              >
                {example}
              </button>
            ))}
          </div>

          <form onSubmit={handleAsk} className="mt-4 space-y-4">
            <label className="block space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] bo-muted">
                Question
              </span>
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={4}
                placeholder='e.g. "Show me all incidents" or "Stock for beef at Chapinero"'
                className="bo-textarea"
                disabled={asking}
              />
            </label>
            <button type="submit" disabled={asking} className="bo-btn-primary">
              {asking ? "Asking…" : "Ask"}
            </button>
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

          {!asking && !askError && answer ? (
            <div className="mt-6 space-y-2">
              <h2 className="text-xs font-semibold uppercase tracking-[0.12em] bo-muted">
                Answer
              </h2>
              <div className="whitespace-pre-wrap rounded-xl border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-answer-bg)] px-4 py-3 text-sm leading-relaxed text-[color:var(--bo-fg)]">
                {answer}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
