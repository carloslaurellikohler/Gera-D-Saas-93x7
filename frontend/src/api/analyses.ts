import { apiDelete, apiGet, apiPostForm } from "./client";
import type {
  AnalysisResponse,
  AnalysisResultResponse,
  AnalysisStatusResponse,
  AnalysisTranscriptionResponse,
  CreateAnalysisPayload,
  PaginatedResponse,
  AnalysisListItem,
  AnalysisStatus,
} from "../types/analysis";

export function listAnalyses(status?: AnalysisStatus) {
  const query = status ? `?status=${status}` : "";
  return apiGet<PaginatedResponse<AnalysisListItem>>(`/analyses${query}`);
}

export function getAnalysis(id: string) {
  return apiGet<AnalysisResponse>(`/analyses/${id}`);
}

export function getAnalysisStatus(id: string) {
  return apiGet<AnalysisStatusResponse>(`/analyses/${id}/status`);
}

export function getTranscription(id: string) {
  return apiGet<AnalysisTranscriptionResponse>(`/analyses/${id}/transcription`);
}

export function getAnalysisResult(id: string) {
  return apiGet<AnalysisResultResponse>(`/analyses/${id}/report?format=json`);
}

export function deleteAnalysis(id: string) {
  return apiDelete(`/analyses/${id}`);
}

export function createAnalysis(payload: CreateAnalysisPayload) {
  const formData = new FormData();
  formData.append("participant_name", payload.participant_name);
  formData.append("objective", payload.objective);
  if (payload.objective_complement) {
    formData.append("objective_complement", payload.objective_complement);
  }
  if (payload.duration_minutes !== undefined) {
    formData.append("duration_minutes", String(payload.duration_minutes));
  }
  if (payload.interaction_date) {
    formData.append("interaction_date", payload.interaction_date);
  }
  if (payload.owner_id) {
    formData.append("owner_id", payload.owner_id);
  }
  formData.append("file", payload.file);

  return apiPostForm<AnalysisResponse>("/analyses", formData);
}
