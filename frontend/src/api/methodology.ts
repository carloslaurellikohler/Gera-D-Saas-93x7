import { apiDelete, apiGet, apiPost, apiPut } from "./client";
import type { MethodologyDetail, MethodologyDraftPayload, MethodologySummary } from "../types/methodology";

export function listMethodologies() {
  return apiGet<MethodologySummary[]>("/methodology");
}

export function getPublishedMethodology() {
  return apiGet<MethodologyDetail>("/methodology/published");
}

export function getMethodology(id: string) {
  return apiGet<MethodologyDetail>(`/methodology/${id}`);
}

export function createMethodologyDraft(fromId?: string) {
  return apiPost<MethodologyDetail>("/methodology/draft", fromId ? { from_id: fromId } : {});
}

export function updateMethodologyDraft(id: string, payload: MethodologyDraftPayload) {
  return apiPut<MethodologyDetail>(`/methodology/${id}`, payload);
}

export function publishMethodology(id: string) {
  return apiPost<MethodologyDetail>(`/methodology/${id}/publish`);
}

export function deleteMethodologyDraft(id: string) {
  return apiDelete(`/methodology/${id}`);
}
