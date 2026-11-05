// Espelha app/models/methodology.py e app/schemas/methodology.py no backend
// (Fase 7; estendido na Fase 9 com o racional estruturado da metodologia V2.1).
import type { CriterionKey } from "./content";

export type MethodologyStatus = "DRAFT" | "PUBLISHED" | "ARCHIVED";

export type FarolColor = "verde" | "amarelo" | "laranja" | "vermelho";

export type AnchorScope = "CRITERION" | "PILLAR";

export type EligibilityEffect = "CAP" | "NOTE";

/** Os cinco pontos de calibração da escala 0–10 (Manual V2.1, seção 8). */
export const ANCHOR_LEVELS = [2, 4, 6, 8, 10] as const;

/** Chaves de pilar aceitas em MethodologyAnchor.scope_key quando scope = "PILLAR". */
export const PILLAR_KEYS = ["pilar_93", "pilar_7"] as const;
export type PillarKey = (typeof PILLAR_KEYS)[number];

export const SUBDIMENSION_LEVEL_COUNT = 5;

export interface MethodologyCategory {
  key: CriterionKey;
  label: string;
  /** O que o critério avalia. */
  description: string;
  order_index: number;
  central_question: string | null;
  what_it_is_not: string | null;
  positive_evidence: string | null;
  negative_evidence: string | null;
  cross_impact_text: string | null;
  /** Peso na nota geral ponderada; a soma dos 6 precisa dar 1. */
  weight: number;
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

/** Descritor observável de um nível da escala, de um critério ou de um pilar. */
export interface MethodologyAnchor {
  scope: AnchorScope;
  scope_key: string;
  level: number;
  descriptor: string;
  order_index: number;
}

/** Fala concreta que caracteriza um nível — o material few-shot do prompt. */
export interface MethodologyAnchorExample {
  criterion_key: CriterionKey;
  level: number;
  scenario: string | null;
  quote: string | null;
  rationale: string;
  order_index: number;
}

/** Rubrica de auditoria 0–4; `levels` tem exatamente 5 itens, índice = nível. */
export interface MethodologySubdimension {
  criterion_key: CriterionKey;
  name: string;
  levels: string[];
  order_index: number;
}

/** Condição observável que impede um critério de alcançar determinada nota. */
export interface MethodologyEligibilityRule {
  /** CriterionKey ou "TRANSVERSAL". */
  scope_key: string;
  condition: string;
  effect: EligibilityEffect;
  max_score: number | null;
  order_index: number;
}

export const TRANSVERSAL_SCOPE_KEY = "TRANSVERSAL";

// --- blocos globais do prompt (JSONB `content`) ------------------------------------
// Validados no backend por MethodologyContentIn; aqui o tipo é frouxo de propósito,
// porque versões antigas podem ter chaves a mais ou a menos.

export interface MethodologyPillar {
  label: string;
  description: string;
}

export interface MethodologyPillars {
  pilar_93: MethodologyPillar;
  pilar_7: MethodologyPillar;
  rule: string;
}

export interface MethodologyEvidenceBasis {
  evidencia: string;
  inferencia_razoavel: string;
  informacao_insuficiente: string;
  rule: string;
}

export interface MethodologyContent extends Record<string, unknown> {
  objective: string;
  unit_of_analysis: string;
  product_principle: string;
  contextual_analysis_principle: string;
  seniority_and_adaptation: string;
  individual_development_not_ranking: string;
  forbidden_behaviors: string[];
  evidence_basis: MethodologyEvidenceBasis;
  pillars: MethodologyPillars;
  evidence_structure: string;
  final_score_rule: string;
  result_potential: { description: string; levels: string[]; rule?: string };
  pb_commercial_potential: { description: string; levels: string[]; warning: string };
  development_taxonomy: {
    pontos_preservados: string;
    riscos: string;
    oportunidades_perdidas: string;
  };
  suggested_questions_rule: string;
  suggested_questions_examples: string[];
  executive_recommendation_rule: string;
  training_notes_rule: string;
  score_format?: string;
  object_evaluated?: string;
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
  content: MethodologyContent;
  categories: MethodologyCategory[];
  calibrators: Calibrator[];
  anchors: MethodologyAnchor[];
  anchor_examples: MethodologyAnchorExample[];
  subdimensions: MethodologySubdimension[];
  eligibility_rules: MethodologyEligibilityRule[];
}

export interface MethodologyDraftPayload {
  calibration_version: string;
  methodology_name: string;
  project: string;
  content: MethodologyContent;
  categories: MethodologyCategory[];
  calibrators: Calibrator[];
  anchors: MethodologyAnchor[];
  anchor_examples: MethodologyAnchorExample[];
  subdimensions: MethodologySubdimension[];
  eligibility_rules: MethodologyEligibilityRule[];
}

/** O system prompt exato que a engine receberá com esta versão. */
export interface MethodologyPromptPreview {
  calibration_version: string;
  system_preamble: string;
  criteria_block: string;
}
