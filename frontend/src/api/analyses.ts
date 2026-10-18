import { apiDelete, apiGet, apiPostForm } from "./client";
import type {
  AnalysisFilters,
  AnalysisQuota,
  AnalysisResponse,
  AnalysisResultResponse,
  AnalysisStatusResponse,
  AnalysisTranscriptionResponse,
  CreateAnalysisPayload,
  PaginatedResponse,
  AnalysisListItem,
} from "../types/analysis";

export function listAnalyses(filters: AnalysisFilters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.participant_name) params.set("participant_name", filters.participant_name);
  if (filters.owner_id) params.set("owner_id", filters.owner_id);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  // Página sem controles de paginação na UI hoje — pede o teto permitido pelo
  // backend (page_size<=100) para os filtros não "sumirem" resultados além das
  // primeiras 20 linhas (default do backend quando page_size não é enviado).
  params.set("page_size", "100");
  return apiGet<PaginatedResponse<AnalysisListItem>>(`/analyses?${params.toString()}`);
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

export function getAnalysisQuota(ownerId?: string) {
  const query = ownerId ? `?owner_id=${ownerId}` : "";
  return apiGet<AnalysisQuota>(`/analyses/quota${query}`);
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
