"use client";

import { FormEvent, useState } from "react";

import { askSupportAgent } from "@/lib/agent";

export default function SupportPage(): React.JSX.Element {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState("");

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
            Same official manuals as the Knowledge tab, but answers run through a
            LangGraph workflow (retrieve → generate or refuse) with server-side
            tracing. Use Knowledge for quick commercial Q&amp;A and reindexing; use
            this tab to exercise the graph-backed agent path.
          </p>
        </header>

        <section className="bo-header">
          <form onSubmit={handleAsk} className="space-y-4">
            <label className="block space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] bo-muted">
                Question
              </span>
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={4}
                placeholder="e.g. How many points do I need for Gold tier?"
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
              Running the support graph (retrieve → answer)…
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
