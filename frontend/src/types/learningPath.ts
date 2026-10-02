import type { ContentResponse, CriterionKey } from "./content";

export interface LearningPathItemResponse {
  content: ContentResponse;
  order_index: number;
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
