"use client";

import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";

import { getAccessToken } from "@/lib/auth-storage";
import {
  appendOutboundUserMessage,
  type AgentChatConnection,
  type AgentChatConnectionState,
  connectAgentChatStream,
  type SupportChatMessage,
} from "@/lib/agent-chat-ws";

const SEND_TIMEOUT_MS = 15_000;
const TURN_TIMEOUT_MS = 90_000;

export interface UseSupportChatWsResult {
  connectionState: AgentChatConnectionState;
  canSend: boolean;
  messages: SupportChatMessage[];
  streaming: boolean;
  pendingTurn: boolean;
  askError: string;
  setAskError: (value: string) => void;
  setMessages: Dispatch<SetStateAction<SupportChatMessage[]>>;
  sendChatMessage: (content: string, interrupt: boolean) => boolean;
  resetChatUi: () => void;
}

/**
 * WebSocket chat hook.
 *
 * Uses callback refs so server ``session_sync`` rehydration is never dropped during
 * React Strict Mode / HMR remounts, and keeps the effect keyed only on ``sessionId``
 * so token refresh handlers do not tear down a live socket.
 */
export function useSupportChatWs(sessionId: string): UseSupportChatWsResult {
  const [connectionState, setConnectionState] =
    useState<AgentChatConnectionState>("connecting");
  const [canSend, setCanSend] = useState(false);
  const [messages, setMessages] = useState<SupportChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [pendingTurn, setPendingTurn] = useState(false);
  const [askError, setAskError] = useState("");

  const connectionRef = useRef<AgentChatConnection | null>(null);
  const messagesRef = useRef<SupportChatMessage[]>([]);
  const pendingSendRef = useRef<{ content: string; interrupt: boolean } | null>(null);

  const setMessagesRef = useRef(setMessages);
  const setStreamingRef = useRef(setStreaming);
  const setPendingTurnRef = useRef(setPendingTurn);
  const setAskErrorRef = useRef(setAskError);
  const setConnectionStateRef = useRef(setConnectionState);
  const setCanSendRef = useRef(setCanSend);

  setMessagesRef.current = setMessages;
  setStreamingRef.current = setStreaming;
  setPendingTurnRef.current = setPendingTurn;
  setAskErrorRef.current = setAskError;
  setConnectionStateRef.current = setConnectionState;
  setCanSendRef.current = setCanSend;

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const trySend = useCallback((content: string, interrupt: boolean): boolean => {
    const connection = connectionRef.current;
    if (!connection?.isLive()) {
      return false;
    }
    return interrupt ? connection.sendInterrupt(content) : connection.sendUserMessage(content);
  }, []);

  const flushPendingSend = useCallback(() => {
    const pending = pendingSendRef.current;
    if (!pending) {
      return;
    }
    if (!trySend(pending.content, pending.interrupt)) {
      return;
    }
    pendingSendRef.current = null;
  }, [trySend]);

  const flushPendingSendRef = useRef(flushPendingSend);
  flushPendingSendRef.current = flushPendingSend;

  useEffect(() => {
    if (!pendingTurn || streaming) {
      return undefined;
    }

    const retryId = window.setInterval(() => {
      flushPendingSendRef.current();
    }, 500);

    const sendTimer = window.setTimeout(() => {
      if (pendingSendRef.current) {
        setAskErrorRef.current(
          "Could not send your question over the chat connection. Wait for Live, then try again.",
        );
        pendingSendRef.current = null;
        setPendingTurnRef.current(false);
      }
    }, SEND_TIMEOUT_MS);

    const turnTimer = window.setTimeout(() => {
      if (!pendingSendRef.current) {
        setAskErrorRef.current(
          "The support agent is taking longer than expected. Try again or start a new conversation.",
        );
        setPendingTurnRef.current(false);
      }
    }, TURN_TIMEOUT_MS);

    return () => {
      window.clearInterval(retryId);
      window.clearTimeout(sendTimer);
      window.clearTimeout(turnTimer);
    };
  }, [pendingTurn, streaming]);

  useEffect(() => {
    if (!sessionId) {
      return undefined;
    }

    const handleBrowserOffline = () => {
      setConnectionStateRef.current("reconnecting");
      setCanSendRef.current(false);
    };

    const handleBrowserOnline = () => {
      connectionRef.current?.syncState();
      flushPendingSendRef.current();
    };

    window.addEventListener("offline", handleBrowserOffline);
    window.addEventListener("online", handleBrowserOnline);

    setConnectionStateRef.current("connecting");
    setCanSendRef.current(false);

    const connection = connectAgentChatStream({
      sessionId,
      getAccessToken,
      getMessages: () => messagesRef.current,
      onMessagesChange: (next) => {
        messagesRef.current = next;
        setMessagesRef.current(next);
        if (next.some((message) => message.role === "assistant")) {
          setPendingTurnRef.current(false);
          setAskErrorRef.current("");
        }
      },
      onStreamingChange: (value) => {
        setStreamingRef.current(value);
        if (value) {
          setPendingTurnRef.current(false);
        }
      },
      onStateChange: (state) => {
        setConnectionStateRef.current(state);
        const live = state === "live" && Boolean(connectionRef.current?.isLive());
        setCanSendRef.current(live);
        if (state === "live") {
          setAskErrorRef.current((current) =>
            current.includes("not ready") || current.includes("Reconnecting")
              ? ""
              : current,
          );
          flushPendingSendRef.current();
        }
      },
      onError: (_code, message) => {
        setAskErrorRef.current(message);
        setPendingTurnRef.current(false);
        pendingSendRef.current = null;
      },
    });

    connectionRef.current = connection;
    connection.syncState();

    return () => {
      window.removeEventListener("offline", handleBrowserOffline);
      window.removeEventListener("online", handleBrowserOnline);
      connection.release();
      connectionRef.current = null;
      setCanSendRef.current(false);
      setConnectionStateRef.current("connecting");
    };
  }, [sessionId]);

  const sendChatMessage = useCallback(
    (content: string, interrupt: boolean): boolean => {
      const trimmed = content.trim();
      if (!trimmed) {
        setAskError("Enter a question before submitting.");
        return false;
      }

      setAskError("");
      setPendingTurn(true);

      if (!interrupt) {
        setMessages((previous) => {
          const next = appendOutboundUserMessage(previous, trimmed);
          messagesRef.current = next;
          return next;
        });
      }

      if (trySend(trimmed, interrupt)) {
        return true;
      }

      pendingSendRef.current = { content: trimmed, interrupt };
      flushPendingSendRef.current();
      return true;
    },
    [trySend],
  );

  const resetChatUi = useCallback(() => {
    messagesRef.current = [];
    setMessages([]);
    setAskError("");
    setPendingTurn(false);
    setStreaming(false);
    pendingSendRef.current = null;
  }, []);

  return {
    connectionState,
    canSend,
    messages,
    streaming,
    pendingTurn,
    askError,
    setAskError,
    setMessages,
    sendChatMessage,
    resetChatUi,
  };
}
