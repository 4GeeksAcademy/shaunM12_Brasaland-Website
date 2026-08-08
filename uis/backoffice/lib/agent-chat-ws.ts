"use client";

import type { SupportTurn } from "@/lib/support-memory-coaching";

export {
  getSupportSessionId,
  resetSupportSessionId,
  SUPPORT_SESSION_STORAGE_KEY,
} from "@/lib/agent-chat-session";

export const EVENT_SESSION_SYNC = "session_sync";
export const EVENT_TOKEN_CHUNK = "token_chunk";
export const EVENT_GENERATION_COMPLETED = "generation_completed";
export const EVENT_GENERATION_INTERRUPTED = "generation_interrupted";
export const EVENT_USER_MESSAGE = "user_message";
export const EVENT_INTERRUPT_REQUESTED = "interrupt_requested";
export const EVENT_ERROR = "error";

export type ChatMessageStatus = "complete" | "interrupted" | "streaming";
export type ChatMessageRole = "user" | "assistant";

export interface SupportChatMessage {
  message_id: string;
  role: ChatMessageRole;
  content: string;
  status: ChatMessageStatus;
  created_at?: string;
}

export type AgentChatConnectionState =
  | "connecting"
  | "live"
  | "reconnecting"
  | "stopped";

export interface AgentChatWireFrame {
  event: string;
  data: Record<string, unknown>;
}

export interface SessionSyncPayload {
  session_id: string;
  messages: SupportChatMessage[];
}

export interface TokenChunkPayload {
  session_id: string;
  message_id: string;
  token: string;
  sequence: number;
}

export interface AgentChatWsClientOptions {
  sessionId: string;
  getAccessToken: () => string | null;
  /** Current UI message list — used to merge token_chunk without dropping optimistic rows. */
  getMessages: () => SupportChatMessage[];
  onMessagesChange: (messages: SupportChatMessage[]) => void;
  onStreamingChange?: (streaming: boolean) => void;
  onStateChange?: (state: AgentChatConnectionState) => void;
  onError?: (code: string, message: string) => void;
}

const SESSION_TEARDOWN_GRACE_MS = 500;

function getAgentBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_AGENT_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}

/** Same-origin `/api/agent/chat/ws` or direct `{base}/agent/chat/ws`. */
export function resolveAgentChatWsPath(): string {
  const prefix = getAgentBaseUrl() ? "/agent" : "/api/agent";
  return `${prefix}/chat/ws`;
}

export function resolveAgentChatWsUrl(sessionId: string, accessToken: string): string {
  const params = new URLSearchParams({
    session_id: sessionId,
    access_token: accessToken,
  });
  const query = params.toString();
  const base = getAgentBaseUrl();

  if (base) {
    const httpUrl = new URL(base);
    const wsProtocol = httpUrl.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProtocol}//${httpUrl.host}/agent/chat/ws?${query}`;
  }

  if (typeof window === "undefined") {
    return `${resolveAgentChatWsPath()}?${query}`;
  }

  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${wsProtocol}//${window.location.host}${resolveAgentChatWsPath()}?${query}`;
}

export function chatReconnectDelayMs(attempt: number): number {
  return Math.min(1000 * 2 ** Math.max(attempt - 1, 0), 30_000);
}

const WS_CLOSE_UNAUTHORIZED = 4401;

function decodeJwtPayloadSegment(segment: string): Record<string, unknown> | null {
  try {
    const base64 = segment.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    return JSON.parse(atob(padded)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/** True when the JWT payload is missing or within `skewSeconds` of expiry. */
export function isChatAccessTokenExpired(
  token: string,
  skewSeconds = 30,
  nowMs: number = Date.now(),
): boolean {
  const segment = token.split(".")[1];
  if (!segment) {
    return true;
  }
  const payload = decodeJwtPayloadSegment(segment);
  if (payload === null || typeof payload.exp !== "number") {
    return true;
  }
  return payload.exp * 1000 <= nowMs + skewSeconds * 1000;
}

/** Prefer a stored access token; refresh when missing or expired. */
export async function resolveChatAccessToken(
  getAccessToken: () => string | null,
): Promise<string | null> {
  const stored = getAccessToken();
  if (stored && !isChatAccessTokenExpired(stored)) {
    return stored;
  }
  const { refreshAccessToken } = await import("@/lib/http");
  return refreshAccessToken();
}

export function parseAgentChatWireFrame(raw: string): AgentChatWireFrame {
  const parsed = JSON.parse(raw) as AgentChatWireFrame;
  if (!parsed || typeof parsed.event !== "string" || typeof parsed.data !== "object") {
    throw new Error("Invalid agent chat WebSocket frame.");
  }
  return parsed;
}

function normalizeSyncMessage(raw: Record<string, unknown>): SupportChatMessage {
  return {
    message_id: String(raw.message_id ?? ""),
    role: raw.role === "assistant" ? "assistant" : "user",
    content: String(raw.content ?? ""),
    status:
      raw.status === "interrupted" || raw.status === "streaming"
        ? raw.status
        : "complete",
    created_at: raw.created_at ? String(raw.created_at) : undefined,
  };
}

export function parseSessionSyncPayload(data: Record<string, unknown>): SessionSyncPayload {
  const messages = Array.isArray(data.messages)
    ? data.messages.map((row) =>
        normalizeSyncMessage(row as Record<string, unknown>),
      )
    : [];
  return {
    session_id: String(data.session_id ?? ""),
    messages,
  };
}

export function parseTokenChunkPayload(data: Record<string, unknown>): TokenChunkPayload {
  return {
    session_id: String(data.session_id ?? ""),
    message_id: String(data.message_id ?? ""),
    token: String(data.token ?? ""),
    sequence: Number(data.sequence ?? 0),
  };
}

export function applySessionSync(
  current: SupportChatMessage[],
  payload: SessionSyncPayload,
): SupportChatMessage[] {
  const synced = payload.messages.map((message) => ({ ...message }));
  // Reconnect race: never wipe a visible transcript when the server sends an empty sync.
  if (synced.length === 0 && current.length > 0) {
    return current.map((message) => ({ ...message }));
  }
  const localOnly = current.filter(
    (message) =>
      message.message_id.startsWith("local-") &&
      !synced.some(
        (row) => row.role === message.role && row.content === message.content,
      ),
  );
  return [...synced, ...localOnly];
}

export function applyTokenChunk(
  current: SupportChatMessage[],
  chunk: TokenChunkPayload,
): SupportChatMessage[] {
  const next = current.map((message) => ({ ...message }));
  const index = next.findIndex((message) => message.message_id === chunk.message_id);
  if (index >= 0) {
    const existing = next[index];
    next[index] = {
      ...existing,
      content: `${existing.content}${chunk.token}`,
      status: "streaming",
    };
    return next;
  }

  next.push({
    message_id: chunk.message_id,
    role: "assistant",
    content: chunk.token,
    status: "streaming",
  });
  return next;
}

export function applyGenerationCompleted(
  current: SupportChatMessage[],
  messageId: string,
): SupportChatMessage[] {
  return current.map((message) =>
    message.message_id === messageId
      ? { ...message, status: "complete" }
      : message,
  );
}

export function applyGenerationInterrupted(
  current: SupportChatMessage[],
  messageId: string,
): SupportChatMessage[] {
  return current.map((message) =>
    message.message_id === messageId
      ? { ...message, status: "interrupted" }
      : message,
  );
}

export function isAssistantStreaming(messages: readonly SupportChatMessage[]): boolean {
  return messages.some(
    (message) => message.role === "assistant" && message.status === "streaming",
  );
}

/** Optimistic local row — server persists user messages but does not echo them on the WS. */
export function appendOutboundUserMessage(
  current: SupportChatMessage[],
  content: string,
  messageId: string = `local-${crypto.randomUUID()}`,
): SupportChatMessage[] {
  const trimmed = content.trim();
  if (!trimmed) {
    return current;
  }
  return [
    ...current,
    {
      message_id: messageId,
      role: "user",
      content: trimmed,
      status: "complete",
    },
  ];
}

export function supportTurnsFromMessages(
  messages: readonly SupportChatMessage[],
): SupportTurn[] {
  const turns: SupportTurn[] = [];
  for (let index = 0; index < messages.length; index += 1) {
    const message = messages[index];
    if (message.role !== "user") {
      continue;
    }
    const next = messages[index + 1];
    if (next?.role === "assistant") {
      turns.push({ question: message.content, answer: next.content });
      index += 1;
    }
  }
  return turns;
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = window.setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      window.clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

export interface AgentChatConnection {
  sendUserMessage: (content: string) => boolean;
  sendInterrupt: (newInput: string) => boolean;
  isLive: () => boolean;
  /** Reconcile UI connection state with the underlying WebSocket. */
  syncState: () => void;
  /** Drop one React subscriber; closes the socket after a short grace when none remain. */
  release: () => void;
}

interface AgentChatSessionEntry {
  optionsRef: { current: AgentChatWsClientOptions };
  connection: AgentChatConnection;
  abortController: AbortController;
  refCount: number;
  teardownTimer: ReturnType<typeof setTimeout> | null;
}

const agentChatSessions = new Map<string, AgentChatSessionEntry>();

/** Test-only: reset module-level session registry. */
export function resetAgentChatSessionsForTests(): void {
  for (const entry of agentChatSessions.values()) {
    if (entry.teardownTimer !== null) {
      clearTimeout(entry.teardownTimer);
    }
    entry.abortController.abort();
  }
  agentChatSessions.clear();
}

function formatOutboundFrame(event: string, data: Record<string, unknown>): string {
  return JSON.stringify({ event, data });
}

function browserIsOnline(): boolean {
  return typeof navigator === "undefined" || navigator.onLine;
}

function runAgentChatClient(
  optionsRef: { current: AgentChatWsClientOptions },
  connection: AgentChatConnection,
  signal: AbortSignal,
): Promise<void> {
  const options = () => optionsRef.current;

  let attempt = 0;
  let socket: WebSocket | null = null;
  let channelReady = false;

  const closeActiveSocket = () => {
    if (socket === null) {
      return;
    }
    const active = socket;
    socket = null;
    active.close();
  };

  signal.addEventListener("abort", closeActiveSocket);

  const publishMessages = (next: SupportChatMessage[]) => {
    options().onMessagesChange(next);
    options().onStreamingChange?.(isAssistantStreaming(next));
  };

  const handleFrame = (frame: AgentChatWireFrame) => {
    switch (frame.event) {
      case EVENT_SESSION_SYNC: {
        const payload = parseSessionSyncPayload(frame.data);
        publishMessages(applySessionSync(options().getMessages(), payload));
        if (!signal.aborted) {
          channelReady = true;
          attempt = 0;
          options().onStateChange?.("live");
        }
        return;
      }
      case EVENT_TOKEN_CHUNK: {
        publishMessages(
          applyTokenChunk(
            options().getMessages(),
            parseTokenChunkPayload(frame.data),
          ),
        );
        return;
      }
      case EVENT_GENERATION_COMPLETED: {
        const messageId = String(frame.data.message_id ?? "");
        publishMessages(applyGenerationCompleted(options().getMessages(), messageId));
        return;
      }
      case EVENT_GENERATION_INTERRUPTED: {
        const messageId = String(frame.data.message_id ?? "");
        publishMessages(applyGenerationInterrupted(options().getMessages(), messageId));
        return;
      }
      case EVENT_ERROR: {
        options().onError?.(
          String(frame.data.code ?? "error"),
          String(frame.data.message ?? "Support chat error."),
        );
        return;
      }
      default:
        return;
    }
  };

  const syncConnectionState = () => {
    if (signal.aborted) {
      return;
    }
    if (!browserIsOnline()) {
      options().onStateChange?.("reconnecting");
      return;
    }
    if (socket !== null && socket.readyState === WebSocket.OPEN && channelReady) {
      options().onStateChange?.("live");
      return;
    }
    if (socket?.readyState === WebSocket.CONNECTING) {
      options().onStateChange?.(attempt > 0 ? "reconnecting" : "connecting");
      return;
    }
    options().onStateChange?.(attempt > 0 ? "reconnecting" : "connecting");
  };

  const markReconnecting = () => {
    channelReady = false;
    if (!signal.aborted) {
      options().onStateChange?.("reconnecting");
    }
  };

  connection.isLive = () =>
    browserIsOnline() &&
    socket !== null &&
    socket.readyState === WebSocket.OPEN &&
    channelReady;

  connection.syncState = syncConnectionState;

  const handleBrowserOffline = () => {
    channelReady = false;
    markReconnecting();
    if (socket !== null && socket.readyState === WebSocket.OPEN) {
      socket.close();
    }
  };

  const handleBrowserOnline = () => {
    if (signal.aborted) {
      return;
    }
    if (connection.isLive()) {
      syncConnectionState();
      return;
    }
    attempt = 0;
    if (socket !== null && socket.readyState !== WebSocket.CLOSED) {
      socket.close();
    } else {
      syncConnectionState();
    }
  };

  const handleVisibilityChange = () => {
    if (signal.aborted || document.visibilityState !== "visible") {
      return;
    }
    if (!browserIsOnline()) {
      return;
    }
    if (!connection.isLive()) {
      handleBrowserOnline();
    }
  };

  if (typeof window !== "undefined") {
    window.addEventListener("offline", handleBrowserOffline);
    window.addEventListener("online", handleBrowserOnline);
    document.addEventListener("visibilitychange", handleVisibilityChange);
  }

  connection.sendUserMessage = (content: string): boolean => {
    if (!connection.isLive()) {
      return false;
    }
    try {
      socket!.send(
        formatOutboundFrame(EVENT_USER_MESSAGE, {
          session_id: options().sessionId,
          content,
        }),
      );
      return true;
    } catch {
      return false;
    }
  };

  connection.sendInterrupt = (newInput: string): boolean => {
    if (!connection.isLive()) {
      return false;
    }
    try {
      socket!.send(
        formatOutboundFrame(EVENT_INTERRUPT_REQUESTED, {
          session_id: options().sessionId,
          new_input: newInput,
        }),
      );
      return true;
    } catch {
      return false;
    }
  };

  const connectOnce = async (): Promise<number | undefined> => {
    if (signal.aborted) {
      return undefined;
    }

    const accessToken = await resolveChatAccessToken(options().getAccessToken);
    if (signal.aborted) {
      return undefined;
    }
    if (!accessToken) {
      throw new Error("Missing access token for support chat.");
    }

    return new Promise((resolve) => {
      if (signal.aborted) {
        resolve(undefined);
        return;
      }

      const ws = new WebSocket(
        resolveAgentChatWsUrl(options().sessionId, accessToken),
      );
      socket = ws;
      channelReady = false;
      syncConnectionState();

      const onAbort = () => {
        ws.close();
      };
      signal.addEventListener("abort", onAbort);

      ws.onopen = () => {
        if (signal.aborted) {
          ws.close();
          return;
        }
        attempt = 0;
        syncConnectionState();
      };

      ws.onmessage = (event) => {
        try {
          handleFrame(parseAgentChatWireFrame(String(event.data)));
        } catch {
          options().onError?.(
            "invalid_frame",
            "Received an invalid chat message from the server.",
          );
        }
      };

      ws.onclose = (event) => {
        signal.removeEventListener("abort", onAbort);
        socket = null;
        channelReady = false;
        if (!signal.aborted) {
          markReconnecting();
        }
        resolve(event.code);
      };
    });
  };

  return (async () => {
    try {
      while (!signal.aborted) {
        if (attempt === 0) {
          if (!signal.aborted) {
            options().onStateChange?.("connecting");
          }
        } else {
          if (!signal.aborted) {
            options().onStateChange?.("reconnecting");
          }
          try {
            await sleep(chatReconnectDelayMs(attempt), signal);
          } catch {
            break;
          }
        }

        if (signal.aborted) {
          break;
        }

        try {
          const closeCode = await connectOnce();
          if (signal.aborted) {
            break;
          }
          if (closeCode === WS_CLOSE_UNAUTHORIZED) {
            const { refreshAccessToken } = await import("@/lib/http");
            await refreshAccessToken();
            if (signal.aborted) {
              break;
            }
          }
        } catch (caught) {
          if (signal.aborted) {
            break;
          }
          options().onError?.(
            "connect_failed",
            caught instanceof Error ? caught.message : "Could not connect to support chat.",
          );
        }

        if (signal.aborted) {
          break;
        }

        attempt += 1;
      }
    } finally {
      if (typeof window !== "undefined") {
        window.removeEventListener("offline", handleBrowserOffline);
        window.removeEventListener("online", handleBrowserOnline);
        document.removeEventListener("visibilitychange", handleVisibilityChange);
      }
      signal.removeEventListener("abort", closeActiveSocket);
      closeActiveSocket();
      if (!signal.aborted) {
        options().onStateChange?.("stopped");
      }
    }
  })();
}

function releaseAgentChatSession(sessionId: string): void {
  const entry = agentChatSessions.get(sessionId);
  if (!entry) {
    return;
  }

  entry.refCount -= 1;
  if (entry.refCount > 0) {
    return;
  }

  if (entry.teardownTimer !== null) {
    clearTimeout(entry.teardownTimer);
  }

  entry.teardownTimer = setTimeout(() => {
    const current = agentChatSessions.get(sessionId);
    if (!current || current.refCount > 0) {
      return;
    }
    current.abortController.abort();
    agentChatSessions.delete(sessionId);
  }, SESSION_TEARDOWN_GRACE_MS);
}

/** Start or join the WebSocket chat client for ``sessionId`` (survives Strict Mode remounts). */
export function connectAgentChatStream(
  options: AgentChatWsClientOptions,
): AgentChatConnection {
  const existing = agentChatSessions.get(options.sessionId);
  if (existing) {
    if (existing.teardownTimer !== null) {
      clearTimeout(existing.teardownTimer);
      existing.teardownTimer = null;
    }
    existing.optionsRef.current = options;
    existing.refCount += 1;
    existing.connection.syncState();
    return existing.connection;
  }

  const optionsRef = { current: options };
  const abortController = new AbortController();
  const connection: AgentChatConnection = {
    sendUserMessage: () => false,
    sendInterrupt: () => false,
    isLive: () => false,
    syncState: () => {},
    release: () => releaseAgentChatSession(options.sessionId),
  };

  agentChatSessions.set(options.sessionId, {
    optionsRef,
    connection,
    abortController,
    refCount: 1,
    teardownTimer: null,
  });

  void runAgentChatClient(optionsRef, connection, abortController.signal);
  return connection;
}
