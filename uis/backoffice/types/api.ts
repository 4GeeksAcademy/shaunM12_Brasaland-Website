export type CandidateStatus = "received" | "in_progress" | "selected" | "discarded";

export type CandidateStage =
  | "pending"
  | "review"
  | "personal_interview"
  | "technical_interview"
  | "offer_presented";

export interface Candidate {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string;
  cv_url: string;
  status: CandidateStatus;
  stage: CandidateStage;
  experience_years: number;
  notes_count?: number;
  applied_at?: string;
  updated_at?: string;
}

export interface CandidateInput {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string;
  cv_url: string;
  status: CandidateStatus;
  stage: CandidateStage;
  experience_years: number;
}

export interface CandidatePatchInput {
  status?: CandidateStatus;
  stage?: CandidateStage;
}

export interface CandidateNote {
  id: string;
  content: string;
  created_at?: string;
}

export type AsyncState = "idle" | "loading" | "success" | "error";
