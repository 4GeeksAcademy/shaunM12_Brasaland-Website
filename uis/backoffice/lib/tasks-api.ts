/** Celery task status API client (DEV-55). */

import { formatApiError } from "@/lib/api-error";
import { authorizedFetch } from "@/lib/http";

export interface TaskStatus {
  task_id: string;
  status: "pending" | "started" | "success" | "failure" | string;
  result: unknown;
}

function getBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_TASKS_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}

/** Same-origin `/api/tasks/*` proxies to FastAPI `/tasks/*`. */
export function taskPath(taskId: string): string {
  const prefix = getBaseUrl() ? "/tasks" : "/api/tasks";
  return `${prefix}/${encodeURIComponent(taskId)}`;
}

export async function fetchTaskStatus(taskId: string): Promise<TaskStatus> {
  let response: Response;
  try {
    response = await authorizedFetch(`${getBaseUrl()}${taskPath(taskId)}`);
  } catch (caught) {
    if (caught instanceof Error && caught.message.toLowerCase().includes("session")) {
      throw caught;
    }
    throw new Error(
      "Cannot reach the tasks API. Start it with: npm run api:dev",
    );
  }

  const body = await response.text();
  if (!response.ok) {
    throw new Error(formatApiError(response.status, body));
  }
  return JSON.parse(body) as TaskStatus;
}
