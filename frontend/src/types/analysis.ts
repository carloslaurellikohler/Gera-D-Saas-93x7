export const OBJECTIVES = [
  "Onboarding",
  "Reunião de alinhamento",
  "Feedback",
  "Entrevista",
  "1:1",
  "Reunião comercial",
  "Avaliação",
  "Outro",
] as const;

export type Objective = (typeof OBJECTIVES)[number];

export type AnalysisStatus =
  | "CREATED"
  | "UPLOADED"
  | "TRANSCRIBING"
  | "TRANSCRIBED"
  | "ANALYZING"
  | "GENERATING_REPORTS"
  | "COMPLETED"
  | "FAILED";

export interface AnalysisListItem {
  id: string;
  participant_name: string;
  objective: string;
  status: AnalysisStatus;
  created_at: string;
}

export interface AnalysisResponse {
  id: string;
  participant_name: string;
  objective: string;
  objective_complement: string | null;
  duration_seconds: number | null;
  interaction_date: string | null;
  input_type: string;
  file_name: string | null;
  status: AnalysisStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface AnalysisStatusResponse {
  id: string;
  status: AnalysisStatus;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string | null;
}

export interface TranscriptTurn {
  speaker: string | null;
  text: string;
}

export interface Transcript {
  turns: TranscriptTurn[];
  is_diarized: boolean;
  source_kind: string;
  raw_summary: string | null;
}

export interface AnalysisTranscriptionResponse {
  id: string;
  transcription: Transcript;
}

export interface CriterionScore {
  key: string;
  label: string;
  score: number;
  reading: string;
  analysis: string;
}

export interface DevelopmentItem {
  title: string;
  description: string;
}

export interface SuggestedQuestion {
  question: string;
  rationale: string;
}

export interface AnalysisResultData {
  pb_name: string;
  cs_name: string;
  overall_score: number;
  overall_band_label: string;
  overall_farol_level: string;
  overall_classification_text: string;
  executive_diagnosis: string;
  general_reading: string;
  scores_by_criterion: CriterionScore[];
  strengths: DevelopmentItem[];
  risks: DevelopmentItem[];
  missed_opportunities: DevelopmentItem[];
  suggested_questions: SuggestedQuestion[];
  executive_recommendation: string;
  final_evaluation: string;
}

export interface AnalysisResultResponse {
  id: string;
  analysis_result: AnalysisResultData;
}

export interface CreateAnalysisPayload {
  participant_name: string;
  objective: Objective;
  objective_complement?: string;
  duration_minutes?: number;
  interaction_date?: string;
  owner_id?: string;
  file: File;
}

export interface AnalysisQuota {
  owner_id: string;
  used: number;
  limit: number;
  remaining: number;
  exempt: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
