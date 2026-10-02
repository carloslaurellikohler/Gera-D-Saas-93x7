import { apiDelete, apiGet, apiPostForm, apiPutForm } from "./client";
import type { ContentResponse, CreateContentPayload, CriterionKey, UpdateContentPayload } from "../types/content";

export function listContent(criterionKey?: CriterionKey) {
  const query = criterionKey ? `?criterion_key=${criterionKey}` : "";
  return apiGet<ContentResponse[]>(`/content${query}`);
}

export function createContent(payload: CreateContentPayload) {
  const formData = new FormData();
  formData.append("title", payload.title);
  if (payload.description) {
    formData.append("description", payload.description);
  }
  if (payload.criterion_key) {
    formData.append("criterion_key", payload.criterion_key);
  }
  formData.append("kind", payload.kind);
  if (payload.file) {
    formData.append("file", payload.file);
  }
  if (payload.external_url) {
    formData.append("external_url", payload.external_url);
  }

  return apiPostForm<ContentResponse>("/content", formData);
}

export function updateContent(id: string, payload: UpdateContentPayload) {
  const formData = new FormData();
  formData.append("title", payload.title);
  if (payload.description) {
    formData.append("description", payload.description);
  }
  if (payload.criterion_key) {
    formData.append("criterion_key", payload.criterion_key);
  }
  if (payload.file) {
    formData.append("file", payload.file);
  }
  if (payload.external_url) {
    formData.append("external_url", payload.external_url);
  }

  return apiPutForm<ContentResponse>(`/content/${id}`, formData);
}

export function deleteContent(id: string) {
  return apiDelete(`/content/${id}`);
}
