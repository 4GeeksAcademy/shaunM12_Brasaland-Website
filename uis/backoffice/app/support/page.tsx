"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { resetSupportSessionId } from "@/lib/agent";
import { SUPPORT_SESSION_STORAGE_KEY } from "@/lib/agent-chat-session";
import {
  getSupportSessionId,
  isAssistantStreaming,
  type AgentChatConnectionState,
  type SupportChatMessage,
  supportTurnsFromMessages,
} from "@/lib/agent-chat-ws";
import {
  MEMORY_APPROVE_PHRASE,
  clearedMemoryMessage,
  getMemoryCoachingState,
  isBareAssent,
} from "@/lib/support-memory-coaching";
import { useSupportChatWs } from "@/lib/use-support-chat-ws";

function connectionStatusLabel(
  state: AgentChatConnectionState,
  sessionReady: boolean,
): string {
  if (!sessionReady) {
    return "Preparing session…";
  }
  switch (state) {
    case "live":
      return "Live";
    case "connecting":
      return "Connecting…";
    case "reconnecting":
      return "Reconnecting…";
    case "stopped":
      return "Disconnected";
    default:
      return "Connecting…";
  }
}

function connectionStatusClass(state: AgentChatConnectionState, sessionReady: boolean): string {
  const base =
    "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold";
  if (!sessionReady || state === "connecting" || state === "reconnecting") {
    return `${base} border-[color:var(--bo-panel-border)] bg-[color:var(--bo-row-bg)] bo-muted`;
  }
  if (state === "live") {
    return `${base} border-[color:var(--bo-accent)]/40 bg-[color:var(--bo-accent-soft)] text-[color:var(--bo-accent)]`;
  }
  return `${base} border-[color:var(--bo-panel-border)] bg-[color:var(--bo-row-bg)] bo-muted`;
}

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

function assistantBubbleClass(status: SupportChatMessage["status"]): string {
  const base =
    "whitespace-pre-wrap rounded-lg border px-3 py-2 text-sm leading-relaxed text-[color:var(--bo-fg)]";
  if (status === "interrupted") {
    return `${base} border-[color:var(--bo-accent)]/50 bg-[color:var(--bo-accent-soft)]/40`;
  }
  return `${base} border-[color:var(--bo-panel-border)] bg-[color:var(--bo-answer-bg)]`;
}

export default function SupportPage(): React.JSX.Element {
  // Storage is unavailable during SSR — hydrate the id after mount.
  const [sessionId, setSessionId] = useState("");
  useEffect(() => {
    setSessionId(getSupportSessionId());
  }, []);

  const {
    connectionState: wsConnectionState,
    canSend: chatCanSend,
    messages,
    streaming,
    pendingTurn,
    askError,
    setAskError,
    setMessages,
    sendChatMessage,
    resetChatUi,
  } = useSupportChatWs(sessionId);

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== SUPPORT_SESSION_STORAGE_KEY || !event.newValue) {
        return;
      }
      setSessionId(event.newValue);
      resetChatUi();
      setQuestion("");
      setCopyFeedback("");
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [resetChatUi]);

  const [question, setQuestion] = useState("");
  const [tipsOpen, setTipsOpen] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState("");

  const inConversation = messages.length > 0;
  const turns = useMemo(() => supportTurnsFromMessages(messages), [messages]);
  const memoryCoaching = useMemo(() => getMemoryCoachingState(turns), [turns]);
  const showBareAssentWarning =
    memoryCoaching?.kind === "awaiting_approval" && isBareAssent(question);
  const busy = streaming || pendingTurn;
  const submitEnabled = chatCanSend && (!busy || streaming);
  const sessionReady = Boolean(sessionId);
  const connectionLabel = connectionStatusLabel(wsConnectionState, sessionReady);

  const handleNewConversation = () => {
    const nextSessionId = resetSupportSessionId();
    setSessionId(nextSessionId);
    setQuestion("");
    resetChatUi();
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

  const handleAsk = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setAskError("Enter a question before submitting.");
      return;
    }

    const interrupt = isAssistantStreaming(messages);
    if (!sendChatMessage(trimmed, interrupt)) {
      return;
    }
    setQuestion("");
  };

  return (
    <main className="bo-page">
      <div className="bo-container-narrow space-y-6">
        <header className="bo-header">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="bo-eyebrow">Brasaland Support Agent</p>
              <h1 className="bo-title">Ask the traceable support agent</h1>
              <p className="bo-lead max-w-2xl">
                Live incidents and inventory stock via MCP and direct APIs, plus knowledge-base
                policies. Answers run through a LangGraph workflow with server-side tracing.
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <span
                className={connectionStatusClass(wsConnectionState, sessionReady)}
                aria-live="polite"
              >
                {wsConnectionState === "live" ? (
                  <span
                    className="h-1.5 w-1.5 rounded-full bg-[color:var(--bo-accent)]"
                    aria-hidden
                  />
                ) : null}
                {connectionLabel}
              </span>
              {sessionReady ? (
                <p className="max-w-xs text-right font-mono text-[10px] leading-snug bo-muted">
                  Session{" "}
                  <span title={sessionId}>{sessionId.slice(0, 8)}…</span>
                  {" · "}
                  {messages.length} message{messages.length === 1 ? "" : "s"}
                  {chatCanSend ? " · ready" : " · not ready"}
                </p>
              ) : null}
            </div>
          </div>
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
              <li>
                Two-tab test: duplicate this tab (same Session id in the header), wait for{" "}
                <strong>Live</strong>, then ask in one tab — the other should show the same answer.
              </li>
            </ul>
          ) : null}

          <div className="mt-4 flex flex-wrap gap-2">
            {EXAMPLE_QUESTIONS.map((example) => (
              <button
                key={example}
                type="button"
                disabled={busy}
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

          {messages.length > 0 ? (
            <div className="mt-6 space-y-3" aria-live="polite">
              {messages.map((message) => (
                <article
                  key={message.message_id}
                  className="rounded-xl border border-[color:var(--bo-panel-border)] bg-[color:var(--bo-panel-bg)] p-4"
                >
                  <h2 className="text-xs font-semibold uppercase tracking-[0.12em] bo-muted">
                    {message.role === "user" ? "You asked" : "Answer"}
                    {message.status === "interrupted" ? " (interrupted)" : null}
                    {message.status === "streaming" ? " (streaming…)" : null}
                  </h2>
                  <div
                    className={
                      message.role === "user"
                        ? "mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[color:var(--bo-fg)]"
                        : `mt-2 ${assistantBubbleClass(message.status)}`
                    }
                    aria-live={message.status === "streaming" ? "polite" : undefined}
                  >
                    {message.content || (message.status === "streaming" ? "…" : "")}
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
                  disabled={busy}
                  className="rounded-full border border-[color:var(--bo-accent)] bg-[color:var(--bo-panel-bg)] px-3 py-1.5 text-xs font-medium text-[color:var(--bo-accent)] transition hover:bg-[color:var(--bo-answer-bg)] disabled:opacity-50"
                  onClick={handleUseApprovePhrase}
                >
                  Use: {MEMORY_APPROVE_PHRASE}
                </button>
                <button
                  type="button"
                  disabled={busy}
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
                  disabled={busy}
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
                    : streaming
                      ? "Type a redirect — this will interrupt the current answer"
                      : inConversation
                        ? `e.g. "${MEMORY_APPROVE_PHRASE}" or a follow-up question`
                        : 'e.g. "Show me all incidents" or "Stock for beef at Chapinero"'
                }
                className="bo-textarea"
                disabled={busy && !streaming}
              />
            </label>

            {showBareAssentWarning ? (
              <p className="text-sm text-[color:var(--bo-error-fg)]" role="status">
                Bare &quot;yes&quot; won&apos;t confirm memory. Use &quot;{MEMORY_APPROVE_PHRASE}
                &quot; instead.
              </p>
            ) : null}

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={!submitEnabled}
                className="bo-btn-primary"
              >
                {streaming
                  ? "Interrupt & send"
                  : pendingTurn
                    ? "Asking…"
                    : "Ask"}
              </button>
              <button
                type="button"
                disabled={busy}
                className="bo-btn-secondary"
                onClick={handleNewConversation}
              >
                New conversation
              </button>
            </div>
          </form>

          {pendingTurn && !streaming ? (
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
