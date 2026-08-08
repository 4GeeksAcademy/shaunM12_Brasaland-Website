import { describe, expect, it } from "vitest";

import {
  applyGenerationCompleted,
  applyGenerationInterrupted,
  applySessionSync,
  applyTokenChunk,
  appendOutboundUserMessage,
  chatReconnectDelayMs,
  EVENT_GENERATION_INTERRUPTED,
  EVENT_SESSION_SYNC,
  EVENT_TOKEN_CHUNK,
  isChatAccessTokenExpired,
  parseAgentChatWireFrame,
  parseSessionSyncPayload,
  parseTokenChunkPayload,
  resolveAgentChatWsPath,
  resolveAgentChatWsUrl,
  supportTurnsFromMessages,
  type SupportChatMessage,
} from "@/lib/agent-chat-ws";

describe("agent chat ws client helpers", () => {
  it("resolves same-origin WebSocket path", () => {
    expect(resolveAgentChatWsPath()).toBe("/api/agent/chat/ws");
  });

  it("builds a browser WebSocket URL with session and token query params", () => {
    const url = resolveAgentChatWsUrl(
      "550e8400-e29b-41d4-a716-446655440000",
      "test-token",
    );
    expect(url).toContain("/api/agent/chat/ws?");
    expect(url).toContain("session_id=550e8400-e29b-41d4-a716-446655440000");
    expect(url).toContain("access_token=test-token");
  });

  it("parses wire frames", () => {
    const frame = parseAgentChatWireFrame(
      JSON.stringify({
        event: EVENT_TOKEN_CHUNK,
        data: {
          session_id: "550e8400-e29b-41d4-a716-446655440000",
          message_id: "7c9e6679-7425-40de-944b-e07fc1f90ae7",
          token: "For",
          sequence: 1,
        },
      }),
    );

    expect(frame.event).toBe(EVENT_TOKEN_CHUNK);
    expect(parseTokenChunkPayload(frame.data).token).toBe("For");
  });

  it("parses session_sync payloads", () => {
    const payload = parseSessionSyncPayload({
      session_id: "550e8400-e29b-41d4-a716-446655440000",
      messages: [
        {
          message_id: "msg-user",
          role: "user",
          content: "Hello",
          status: "complete",
          created_at: "2026-08-07T12:00:00Z",
        },
      ],
    });

    expect(payload.messages).toHaveLength(1);
    expect(payload.messages[0].role).toBe("user");
  });

  it("replaces messages on session_sync", () => {
    const current: SupportChatMessage[] = [
      {
        message_id: "old",
        role: "assistant",
        content: "stale",
        status: "complete",
      },
    ];
    const next = applySessionSync(current, {
      session_id: "550e8400-e29b-41d4-a716-446655440000",
      messages: [
        {
          message_id: "fresh",
          role: "user",
          content: "Hi",
          status: "complete",
        },
      ],
    });

    expect(next).toEqual([
      {
        message_id: "fresh",
        role: "user",
        content: "Hi",
        status: "complete",
      },
    ]);
  });

  it("preserves unsynced optimistic user rows on session_sync", () => {
    const next = applySessionSync(
      [
        {
          message_id: "local-abc",
          role: "user",
          content: "How many open incidents are there?",
          status: "complete",
        },
      ],
      {
        session_id: "550e8400-e29b-41d4-a716-446655440000",
        messages: [],
      },
    );

    expect(next).toHaveLength(1);
    expect(next[0].message_id).toBe("local-abc");
  });

  it("preserves server-backed transcript when session_sync is empty", () => {
    const current: SupportChatMessage[] = [
      {
        message_id: "msg-user",
        role: "user",
        content: "How many open incidents are there?",
        status: "complete",
      },
      {
        message_id: "msg-assistant",
        role: "assistant",
        content: "There are 37 open incidents.",
        status: "complete",
      },
    ];
    const next = applySessionSync(current, {
      session_id: "550e8400-e29b-41d4-a716-446655440000",
      messages: [],
    });

    expect(next).toEqual(current);
  });

  it("appends token_chunk data to the active assistant bubble", () => {
    const first = applyTokenChunk([], {
      session_id: "550e8400-e29b-41d4-a716-446655440000",
      message_id: "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      token: "For ",
      sequence: 1,
    });
    const second = applyTokenChunk(first, {
      session_id: "550e8400-e29b-41d4-a716-446655440000",
      message_id: "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      token: "Miami",
      sequence: 2,
    });

    expect(second).toEqual([
      {
        message_id: "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        role: "assistant",
        content: "For Miami",
        status: "streaming",
      },
    ]);
  });

  it("marks assistant rows complete or interrupted", () => {
    const streaming: SupportChatMessage[] = [
      {
        message_id: "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        role: "assistant",
        content: "Partial",
        status: "streaming",
      },
    ];

    expect(
      applyGenerationInterrupted(streaming, "7c9e6679-7425-40de-944b-e07fc1f90ae7")[0]
        .status,
    ).toBe("interrupted");
    expect(
      applyGenerationCompleted(streaming, "7c9e6679-7425-40de-944b-e07fc1f90ae7")[0]
        .status,
    ).toBe("complete");
  });

  it("appends optimistic user rows for outbound sends", () => {
    const next = appendOutboundUserMessage([], "Show me all incidents", "local-test");
    expect(next).toEqual([
      {
        message_id: "local-test",
        role: "user",
        content: "Show me all incidents",
        status: "complete",
      },
    ]);
  });

  it("derives memory coaching turns from chat messages", () => {
    const turns = supportTurnsFromMessages([
      {
        message_id: "u1",
        role: "user",
        content: "Remember Miami hours",
        status: "complete",
      },
      {
        message_id: "a1",
        role: "assistant",
        content: "Would you like me to remember that?",
        status: "complete",
      },
    ]);

    expect(turns).toEqual([
      {
        question: "Remember Miami hours",
        answer: "Would you like me to remember that?",
      },
    ]);
  });

  it("caps reconnect backoff at 30 seconds", () => {
    expect(chatReconnectDelayMs(1)).toBe(1000);
    expect(chatReconnectDelayMs(6)).toBe(30_000);
  });

  it("detects expired chat access tokens from JWT exp", () => {
    const nowMs = 1_700_000_000_000;
    const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
    const validPayload = btoa(JSON.stringify({ sub: "7", exp: Math.floor(nowMs / 1000) + 3600 }));
    const expiredPayload = btoa(JSON.stringify({ sub: "7", exp: Math.floor(nowMs / 1000) - 60 }));
    const validToken = `${header}.${validPayload}.sig`;
    const expiredToken = `${header}.${expiredPayload}.sig`;

    expect(isChatAccessTokenExpired(validToken, 30, nowMs)).toBe(false);
    expect(isChatAccessTokenExpired(expiredToken, 30, nowMs)).toBe(true);
  });

  it("handles generation_interrupted wire event names", () => {
    const frame = parseAgentChatWireFrame(
      JSON.stringify({
        event: EVENT_GENERATION_INTERRUPTED,
        data: {
          session_id: "550e8400-e29b-41d4-a716-446655440000",
          message_id: "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        },
      }),
    );
    expect(frame.event).toBe(EVENT_GENERATION_INTERRUPTED);
  });

  it("handles session_sync wire event names", () => {
    const frame = parseAgentChatWireFrame(
      JSON.stringify({
        event: EVENT_SESSION_SYNC,
        data: { session_id: "550e8400-e29b-41d4-a716-446655440000", messages: [] },
      }),
    );
    expect(frame.event).toBe(EVENT_SESSION_SYNC);
  });
});
