import type { ContentResponse, CriterionKey } from "./content";

export interface LearningPathItemResponse {
  id: string;
  content: ContentResponse;
  order_index: number;
  completed: boolean;
}

export interface LearningPathSummary {
  id: string;
  title: string;
  description: string | null;
  criterion_key: CriterionKey | null;
  estimated_duration_minutes: number | null;
  item_count: number;
  created_at: string;
}

export interface LearningPathDetail {
  id: string;
  title: string;
  description: string | null;
  criterion_key: CriterionKey | null;
  estimated_duration_minutes: number | null;
  created_at: string;
  items: LearningPathItemResponse[];
}

export interface CreateLearningPathItem {
  content_id: string;
  order_index: number;
}

export interface CreateLearningPathPayload {
  title: string;
  description?: string;
  criterion_key?: CriterionKey;
  estimated_duration_minutes?: number;
  items?: CreateLearningPathItem[];
}

export interface EnrollmentResponse {
  learning_path_id: string;
  enrolled_at: string;
}

export interface EnrolledLearningPathSummary {
  id: string;
  title: string;
  description: string | null;
  criterion_key: CriterionKey | null;
  estimated_duration_minutes: number | null;
  item_count: number;
  completed_count: number;
  progress_percent: number;
  is_completed: boolean;
  enrolled_at: string;
  created_at: string;
}
