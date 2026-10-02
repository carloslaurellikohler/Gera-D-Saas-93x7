import { apiGet } from "./client";
import type { MetricsEvolutionResponse, MetricsPeriod } from "../types/metrics";

export function getMetricsEvolution(period: MetricsPeriod = "6m") {
  return apiGet<MetricsEvolutionResponse>(`/metrics/evolution?period=${period}`);
}
