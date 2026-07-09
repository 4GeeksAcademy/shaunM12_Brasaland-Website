"use client";

import { getAccessToken } from "./auth-storage";
import { getCorrelatedRequestId } from "./request-id";

const TELEMETRY_ENDPOINT =
  process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT?.trim() || "/telemetry/events";
const TELEMETRY_BATCH_SIZE = 20;
const TELEMETRY_FLUSH_MS = 10_000;
const TELEMETRY_MAX_RETRIES = 3;
const SESSION_ID_KEY = "brasaland_telemetry_session_id";
const SESSION_STARTED_AT_KEY = "brasaland_telemetry_session_started_at";
export const LAST_LOCATION_ID_KEY = "brasaland_last_location_id";

const DEBOUNCE_WINDOWS_MS: Record<string, number> = {
  ingredient_list_viewed: 30_000,
  location_filter_applied: 10_000,
};

type TelemetryProperties = Record<string, unknown>;

interface TelemetryEnvelope {
  eventId: string;
  timestamp: string;
  sessionId: string;
  userId: string;
  event_type: string;
  schemaVersion: number;
  requestId: string;
  service: "backoffice";
  properties: TelemetryProperties;
}

interface TelemetryBatch {
  events: TelemetryEnvelope[];
}

let queue: TelemetryEnvelope[] = [];
let flushTimer: number | null = null;
let flushInFlight = false;
let listenersRegistered = false;
const debounceState = new Map<string, number>();

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
}

function nowIso(): string {
  return new Date().toISOString();
}

function readJwtSubject(token: string): string | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) {
      return null;
    }
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = atob(normalized);
    const parsed = JSON.parse(decoded) as { sub?: string | number };
    if (parsed.sub == null) {
      return null;
    }
    return String(parsed.sub);
  } catch {
    return null;
  }
}

function resolveUserId(): string {
  const token = getAccessToken();
  if (!token) {
    return "anonymous";
  }
  return readJwtSubject(token) ?? "anonymous";
}

export function getTelemetrySessionId(): string {
  return getOrCreateSessionId();
}

function getOrCreateSessionId(): string {
  if (typeof window === "undefined") {
    return `sess_${uuid()}`;
  }
  const existing = window.sessionStorage.getItem(SESSION_ID_KEY);
  if (existing) {
    return existing;
  }
  const created = `sess_${uuid()}`;
  window.sessionStorage.setItem(SESSION_ID_KEY, created);
  window.sessionStorage.setItem(SESSION_STARTED_AT_KEY, nowIso());
  return created;
}

function debounceKey(eventType: string, properties: TelemetryProperties): string | null {
  if (
    eventType !== "ingredient_list_viewed" &&
    eventType !== "location_filter_applied"
  ) {
    return null;
  }
  return `${eventType}:${getOrCreateSessionId()}:${String(properties.location_id ?? "")}`;
}

function shouldSkipDebounced(eventType: string, properties: TelemetryProperties): boolean {
  const windowMs = DEBOUNCE_WINDOWS_MS[eventType];
  if (!windowMs) {
    return false;
  }
  const key = debounceKey(eventType, properties);
  if (!key) {
    return false;
  }
  const now = Date.now();
  const last = debounceState.get(key) ?? 0;
  if (now - last < windowMs) {
    return true;
  }
  debounceState.set(key, now);
  return false;
}

function buildEvent(
  eventType: string,
  properties: TelemetryProperties,
): TelemetryEnvelope {
  return {
    eventId: uuid(),
    timestamp: nowIso(),
    sessionId: getOrCreateSessionId(),
    userId: resolveUserId(),
    event_type: eventType,
    schemaVersion: 1,
    requestId: getCorrelatedRequestId(),
    service: "backoffice",
    properties,
  };
}

export function rememberLastLocationId(locationId: number): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(LAST_LOCATION_ID_KEY, String(locationId));
}

export function readLastLocationId(): number | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }
  const raw = window.sessionStorage.getItem(LAST_LOCATION_ID_KEY);
  if (!raw) {
    return undefined;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function scheduleFlush(): void {
  if (flushTimer !== null || typeof window === "undefined") {
    return;
  }
  flushTimer = window.setTimeout(() => {
    flushTimer = null;
    void flushQueue();
  }, TELEMETRY_FLUSH_MS);
}

function clearFlushTimer(): void {
  if (flushTimer !== null && typeof window !== "undefined") {
    window.clearTimeout(flushTimer);
    flushTimer = null;
  }
}

async function postBatch(batch: TelemetryEnvelope[]): Promise<void> {
  const response = await fetch(TELEMETRY_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ events: batch } satisfies TelemetryBatch),
    keepalive: true,
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Telemetry POST failed (${response.status})`);
  }
}

async function flushQueue(): Promise<void> {
  if (flushInFlight || queue.length === 0) {
    return;
  }
  flushInFlight = true;
  clearFlushTimer();

  const batch = queue.slice(0, TELEMETRY_BATCH_SIZE);
  queue = queue.slice(batch.length);

  let sent = false;
  for (let attempt = 0; attempt < TELEMETRY_MAX_RETRIES; attempt += 1) {
    try {
      await postBatch(batch);
      sent = true;
      break;
    } catch {
      const waitMs = 500 * 2 ** attempt;
      await new Promise((resolve) => setTimeout(resolve, waitMs));
    }
  }

  if (!sent) {
    // Discard after retries per Phase 2 requirement.
  }

  flushInFlight = false;
  if (queue.length > 0) {
    void flushQueue();
  }
}

function flushWithBeacon(): void {
  if (typeof navigator === "undefined" || queue.length === 0) {
    return;
  }
  const batch = queue.slice();
  queue = [];
  clearFlushTimer();

  const body = JSON.stringify({ events: batch } satisfies TelemetryBatch);
  const ok = navigator.sendBeacon(
    TELEMETRY_ENDPOINT,
    new Blob([body], { type: "application/json" }),
  );
  if (!ok) {
    void postBatch(batch).catch(() => {});
  }
}

function ensureListeners(): void {
  if (listenersRegistered || typeof document === "undefined") {
    return;
  }
  listenersRegistered = true;
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      flushWithBeacon();
    }
  });
  window.addEventListener("pagehide", flushWithBeacon);
}

export function getSessionDurationSeconds(): number {
  if (typeof window === "undefined") {
    return 0;
  }
  const startedAt = window.sessionStorage.getItem(SESSION_STARTED_AT_KEY);
  if (!startedAt) {
    return 0;
  }
  const deltaMs = Date.now() - new Date(startedAt).getTime();
  if (!Number.isFinite(deltaMs) || deltaMs < 0) {
    return 0;
  }
  return Math.floor(deltaMs / 1000);
}

export function track(eventType: string, properties: TelemetryProperties): void {
  if (typeof window === "undefined") {
    return;
  }
  if (shouldSkipDebounced(eventType, properties)) {
    return;
  }
  ensureListeners();
  queue.push(buildEvent(eventType, properties));
  if (queue.length >= TELEMETRY_BATCH_SIZE) {
    void flushQueue();
    return;
  }
  scheduleFlush();
}
