import { apiDelete, apiGet, apiPost } from "./client";
import type {
  CreateLearningPathPayload,
  EnrolledLearningPathSummary,
  EnrollmentResponse,
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

export function enrollInLearningPath(id: string) {
  return apiPost<EnrollmentResponse>(`/learning-paths/${id}/enroll`);
}

export function listEnrolledLearningPaths() {
  return apiGet<EnrolledLearningPathSummary[]>("/learning-paths/enrolled");
}

export function completeLearningPathItem(learningPathId: string, itemId: string) {
  return apiPost<void>(`/learning-paths/${learningPathId}/items/${itemId}/complete`);
}

export function uncompleteLearningPathItem(learningPathId: string, itemId: string) {
  return apiDelete(`/learning-paths/${learningPathId}/items/${itemId}/complete`);
}
