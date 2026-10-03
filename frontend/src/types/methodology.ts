// Espelha app/models/methodology.py e app/schemas/methodology.py no backend (Fase 7).
import type { CriterionKey } from "./content";

export type MethodologyStatus = "DRAFT" | "PUBLISHED" | "ARCHIVED";

export type FarolColor = "verde" | "amarelo" | "laranja" | "vermelho";

export interface MethodologyCategory {
  key: CriterionKey;
  label: string;
  description: string;
  order_index: number;
  extra: Record<string, string>;
}

export interface Calibrator {
  key: string;
  label: string;
  color: FarolColor;
  min: number;
  max: number;
  order_index: number;
}

export interface MethodologySummary {
  id: string;
  calibration_version: string;
  methodology_name: string;
  status: MethodologyStatus;
  created_at: string;
  published_at: string | null;
  archived_at: string | null;
}

export interface MethodologyDetail extends MethodologySummary {
  project: string;
  content: Record<string, unknown>;
  categories: MethodologyCategory[];
  calibrators: Calibrator[];
}

export interface MethodologyDraftPayload {
  calibration_version: string;
  methodology_name: string;
  project: string;
  content: Record<string, unknown>;
  categories: MethodologyCategory[];
  calibrators: Calibrator[];
}
