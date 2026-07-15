export type IncidentCategory =
  | "CUSTOMER_COMPLAINT"
  | "EQUIPMENT"
  | "SUPPLY"
  | "FOOD_QUALITY"
  | "STAFF";

export type IncidentStatus = "OPEN" | "CLOSED" | "DISCARDED";

/** Manager API category values (centralized incident model). */
export type ManagedIncidentCategory =
  | "equipment_failure"
  | "supply_issue"
  | "customer_complaint"
  | "staff_issue"
  | "facility_issue"
  | "pos_system"
  | "delivery_issue"
  | "other";

export type ManagedIncidentStatus =
  | "open"
  | "in_progress"
  | "resolved"
  | "discarded";

export type ManagedIncidentOrigin = "customer" | "branch" | "internal";

export type ManagedIncidentBranch =
  | "central"
  | "medellin_centro"
  | "medellin_laureles"
  | "medellin_envigado"
  | "medellin_bello"
  | "medellin_itagui"
  | "bogota_chapinero"
  | "bogota_usaquen"
  | "cali_granada"
  | "barranquilla_norte"
  | "miami_doral"
  | "miami_hialeah"
  | "miami_kendall"
  | "orlando_international"
  | "fort_lauderdale";

/** Validated incident row shape produced by the Python analyzer. */
export interface NormalizedIncidentRecord {
  incidentId?: string;
  reportedAt?: string;
  locationId: string;
  category: IncidentCategory;
  status: IncidentStatus;
  reportedBy: string;
  description: string;
  satisfactionIndex?: number;
}

export interface IncidentAnalysisResult {
  sourcePath: string;
  schemaError: string | null;
  totalProcessed: number;
  validCount: number;
  invalidCount: number;
  invalidReasons: Record<string, number>;
  invalidRowSamples: number[];
  byCategory: Record<IncidentCategory, number>;
  byStatus: Record<IncidentStatus, number>;
  avgSatisfactionClosed: number | null;
  satisfactionClosedCount: number;
  closedCaseCount: number;
  satisfactionScoreBreakdown: Record<string, number>;
}

export interface ManagedIncident {
  id: number;
  title: string;
  description: string;
  category: ManagedIncidentCategory;
  status: ManagedIncidentStatus;
  origin: ManagedIncidentOrigin;
  branch: ManagedIncidentBranch;
  created_at: string;
  updated_at: string;
}

export interface ManagedIncidentCreate {
  title: string;
  description: string;
  category: ManagedIncidentCategory;
  status?: ManagedIncidentStatus;
  origin: ManagedIncidentOrigin;
  branch: ManagedIncidentBranch;
}

export interface IncidentManagerSummary {
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_origin: Record<string, number>;
  by_branch: Record<string, number>;
}

export const MANAGED_CATEGORIES: ManagedIncidentCategory[] = [
  "equipment_failure",
  "supply_issue",
  "customer_complaint",
  "staff_issue",
  "facility_issue",
  "pos_system",
  "delivery_issue",
  "other",
];

export const MANAGED_STATUSES: ManagedIncidentStatus[] = [
  "open",
  "in_progress",
  "resolved",
  "discarded",
];

export const MANAGED_ORIGINS: ManagedIncidentOrigin[] = [
  "customer",
  "branch",
  "internal",
];

export const MANAGED_BRANCHES: ManagedIncidentBranch[] = [
  "central",
  "medellin_centro",
  "medellin_laureles",
  "medellin_envigado",
  "medellin_bello",
  "medellin_itagui",
  "bogota_chapinero",
  "bogota_usaquen",
  "cali_granada",
  "barranquilla_norte",
  "miami_doral",
  "miami_hialeah",
  "miami_kendall",
  "orlando_international",
  "fort_lauderdale",
];

/** Allowed next statuses from the incident lifecycle. */
export const STATUS_TRANSITIONS: Record<
  ManagedIncidentStatus,
  ManagedIncidentStatus[]
> = {
  open: ["in_progress", "discarded"],
  in_progress: ["resolved", "discarded"],
  resolved: [],
  discarded: [],
};
