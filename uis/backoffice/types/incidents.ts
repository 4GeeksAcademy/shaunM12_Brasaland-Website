export type IncidentCategory =
  | "CUSTOMER_COMPLAINT"
  | "EQUIPMENT"
  | "SUPPLY"
  | "FOOD_QUALITY"
  | "STAFF";

export type IncidentStatus = "OPEN" | "CLOSED" | "DISCARDED";

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
