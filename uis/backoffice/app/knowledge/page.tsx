"use client";

import { FormEvent, useState } from "react";

import {
  askKnowledgeQuestion,
  reindexKnowledge,
} from "@/lib/knowledge";

export default function KnowledgePage(): React.JSX.Element {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState("");

  const [reindexOpen, setReindexOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [reindexing, setReindexing] = useState(false);
  const [reindexMessage, setReindexMessage] = useState("");
  const [reindexError, setReindexError] = useState("");

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
      const result = await askKnowledgeQuestion(trimmed);
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

  const openReindex = () => {
    setConfirmText("");
    setReindexError("");
    setReindexMessage("");
    setReindexOpen(true);
  };

  const closeReindex = () => {
    if (reindexing) {
      return;
    }
    setReindexOpen(false);
    setConfirmText("");
  };

  const handleReindex = async () => {
    if (confirmText.trim() !== "REINDEX") {
      setReindexError("Type REINDEX to confirm.");
      return;
    }
    setReindexing(true);
    setReindexError("");
    setReindexMessage("");
    try {
      const result = await reindexKnowledge();
      setReindexMessage(
        `Reindex complete — ${result.chunks_indexed} chunks upserted.`,
      );
      setReindexOpen(false);
      setConfirmText("");
    } catch (caught) {
      setReindexError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setReindexing(false);
    }
  };

  return (
    <main className="bo-page">
      <div className="bo-container-narrow space-y-6">
        <header className="bo-header">
          <p className="bo-eyebrow">Brasaland Knowledge</p>
          <h1 className="bo-title">Ask the commercial assistant</h1>
          <p className="bo-lead max-w-2xl">
            Answers are generated from official manuals (loyalty, allergens, waste,
            suppliers) — not raw search hits. Ask like a prospect or location manager.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="button" onClick={openReindex} className="bo-btn-secondary">
              Reindex knowledge base
            </button>
          </div>
          {reindexMessage ? (
            <p className="mt-3 text-sm text-[color:var(--bo-success)]" role="status">
              {reindexMessage}
            </p>
          ) : null}
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
              Searching manuals and drafting an answer…
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

      {reindexOpen ? (
        <div
          className="bo-overlay fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="reindex-title"
        >
          <div className="bo-auth-card max-w-md space-y-0 p-6">
            <h2 id="reindex-title" className="bo-subtitle">
              Confirm reindex
            </h2>
            <p className="mt-2 text-sm bo-muted">
              This refreshes vectors from{" "}
              <code className="text-[color:var(--bo-accent)]">
                docs/company-knowledge-base/
              </code>{" "}
              via upsert (does not wipe the collection). Type{" "}
              <strong className="text-[color:var(--bo-heading)]">REINDEX</strong> to
              continue.
            </p>
            <input
              value={confirmText}
              onChange={(event) => setConfirmText(event.target.value)}
              className="bo-input mt-4"
              placeholder="REINDEX"
              autoComplete="off"
              disabled={reindexing}
            />
            {reindexError ? (
              <p className="mt-2 text-sm text-[color:var(--bo-error-fg)]" role="alert">
                {reindexError}
              </p>
            ) : null}
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={closeReindex}
                disabled={reindexing}
                className="bo-btn-secondary normal-case tracking-normal"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleReindex()}
                disabled={reindexing || confirmText.trim() !== "REINDEX"}
                className="bo-btn-primary disabled:cursor-not-allowed disabled:opacity-50"
              >
                {reindexing ? "Reindexing…" : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
