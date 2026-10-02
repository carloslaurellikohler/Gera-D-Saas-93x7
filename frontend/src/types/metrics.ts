export type MetricsPeriod = "30d" | "90d" | "6m";

export interface CriterionRadarPoint {
  key: string;
  label: string;
  score: number | null;
  previous_score: number | null;
  sample_size: number;
}

export interface MetricsTrendPoint {
  period_start: string;
  count: number;
  avg_overall_score: number | null;
  avg_pilar_93: number | null;
  avg_pilar_7: number | null;
}

export interface MetricsEvolutionResponse {
  period: MetricsPeriod;
  radar: CriterionRadarPoint[];
  trend: MetricsTrendPoint[];
}
