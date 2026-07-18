/** Reporting API client for weekly location performance dashboard. */

import { formatApiError } from "@/lib/api-error";
import { authorizedFetch } from "@/lib/http";

export interface WeeklyLocationPerformanceRow {
  id: string;
  location_id: number;
  country: string;
  week_start: string;
  total_purchase_cost: number;
  total_waste_cost: number;
  waste_ratio: number;
  stockout_events_count: number;
  price_alert_events_count: number;
  currency: string;
  computed_at: string;
}

export interface PipelineRunLatest {
  id: string;
  flow_name: string;
  week_start: string | null;
  period_start: string | null;
  period_end: string | null;
  start_time: string;
  end_time: string | null;
  records_extracted: number;
  records_loaded: number;
  records_processed: number;
  records_skipped_missing_cost: number;
  status: string;
  errors: Record<string, unknown> | null;
}

export interface PipelineRunAccepted {
  task_id: string;
  status: string;
  message: string;
}

function getBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_REPORTING_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}

/** Same-origin `/api/reporting/*` proxies to FastAPI `/reporting/*`. */
function reportingPath(suffix: string): string {
  const prefix = getBaseUrl() ? "/reporting" : "/api/reporting";
  return `${prefix}${suffix}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await authorizedFetch(`${getBaseUrl()}${path}`, init);
  } catch (caught) {
    if (caught instanceof Error && caught.message.toLowerCase().includes("session")) {
      throw caught;
    }
    throw new Error(
      "Cannot reach the reporting API. Start it with: npm run api:dev",
    );
  }

  const body = await response.text();
  if (!response.ok) {
    throw new Error(formatApiError(response.status, body));
  }
  if (!body) {
    return undefined as T;
  }
  return JSON.parse(body) as T;
}

export async function fetchWeeklyLocationPerformance(
  weekStart?: string | null,
): Promise<WeeklyLocationPerformanceRow[]> {
  const query =
    weekStart && weekStart.trim()
      ? `?week_start=${encodeURIComponent(weekStart.trim())}`
      : "";
  return request<WeeklyLocationPerformanceRow[]>(
    reportingPath(`/weekly-location-performance${query}`),
  );
}

export async function fetchLatestPipelineRun(): Promise<PipelineRunLatest | null> {
  try {
    return await request<PipelineRunLatest>(reportingPath("/pipeline-runs/latest"));
  } catch (caught) {
    const message = caught instanceof Error ? caught.message : String(caught);
    if (message.includes("404") || message.toLowerCase().includes("no pipeline")) {
      return null;
    }
    throw caught;
  }
}

export async function triggerPipelineRun(): Promise<PipelineRunAccepted> {
  return request<PipelineRunAccepted>(reportingPath("/pipeline-runs"), {
    method: "POST",
  });
}
