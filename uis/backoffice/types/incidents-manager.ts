export type IncidentManagerStatus = "open" | "in_progress" | "resolved" | "discarded";

export type IncidentManagerOrigin = "customer" | "branch" | "internal";

export type IncidentManagerCategory =
  | "equipment_failure"
  | "supply_issue"
  | "customer_complaint"
  | "staff_issue"
  | "facility_issue"
  | "pos_system"
  | "delivery_issue"
  | "other";

export type IncidentManagerBranch =
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

export interface IncidentManagerRecord {
  id: number;
  title: string;
  description: string;
  category: IncidentManagerCategory;
  status: IncidentManagerStatus;
  origin: IncidentManagerOrigin;
  branch: IncidentManagerBranch;
  created_at: string;
  updated_at: string;
}

export interface IncidentManagerCreateInput {
  title: string;
  description: string;
  category: IncidentManagerCategory;
  origin: IncidentManagerOrigin;
  branch: IncidentManagerBranch;
  status?: IncidentManagerStatus;
}

export interface IncidentManagerSummary {
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_origin: Record<string, number>;
  by_branch: Record<string, number>;
}
