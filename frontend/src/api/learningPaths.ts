import { apiDelete, apiGet, apiPost } from "./client";
import type {
  CreateLearningPathPayload,
  LearningPathDetail,
  LearningPathSummary,
} from "../types/learningPath";

export function listLearningPaths() {
  return apiGet<LearningPathSummary[]>("/learning-paths");
}

export function getRecommendedLearningPaths() {
  return apiGet<LearningPathSummary[]>("/learning-paths/recommended");
}

export function getLearningPath(id: string) {
  return apiGet<LearningPathDetail>(`/learning-paths/${id}`);
}

export function createLearningPath(payload: CreateLearningPathPayload) {
  return apiPost<LearningPathDetail>("/learning-paths", payload);
}

export function deleteLearningPath(id: string) {
  return apiDelete(`/learning-paths/${id}`);
}
