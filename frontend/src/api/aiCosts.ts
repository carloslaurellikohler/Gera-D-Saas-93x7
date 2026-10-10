import { apiGet, apiPost, apiPut } from "./client";
import type {
  AiCostConfig,
  AiCostConfigPayload,
  AiCostPeriod,
  AiCostSummary,
  AiModelPrice,
  AiModelPricePayload,
  AiRecalculateResult,
  AiUnpricedModel,
  AiUsageEventFilters,
  AiUsageEventPage,
} from "../types/aiCost";

export function getAiCostSummary(period: AiCostPeriod = "30d") {
  return apiGet<AiCostSummary>(`/ai-costs/summary?period=${period}`);
}

export function listAiCostEvents(filters: AiUsageEventFilters = {}) {
  const params = new URLSearchParams();
  params.set("period", filters.period ?? "30d");
  if (filters.feature) params.set("feature", filters.feature);
  if (filters.operation) params.set("operation", filters.operation);
  if (filters.model) params.set("model", filters.model);
  if (filters.analysis_id) params.set("analysis_id", filters.analysis_id);
  if (filters.offset) params.set("offset", String(filters.offset));
  if (filters.limit) params.set("limit", String(filters.limit));
  return apiGet<AiUsageEventPage>(`/ai-costs/events?${params.toString()}`);
}

export function listAiModelPrices() {
  return apiGet<AiModelPrice[]>("/ai-costs/prices");
}

export function listUnpricedAiModels() {
  return apiGet<AiUnpricedModel[]>("/ai-costs/unpriced-models");
}

export function createAiModelPrice(payload: AiModelPricePayload) {
  return apiPost<AiModelPrice>("/ai-costs/prices", payload);
}

export function updateAiModelPrice(id: string, payload: AiModelPricePayload) {
  return apiPut<AiModelPrice>(`/ai-costs/prices/${id}`, payload);
}

// Reescreve o custo congelado dos eventos afetados por esta vigência — ação explícita,
// confirmada na UI, nunca automática ao salvar um preço.
export function recalculateAiModelPrice(id: string) {
  return apiPost<AiRecalculateResult>(`/ai-costs/prices/${id}/recalculate`);
}

export function getAiCostConfig() {
  return apiGet<AiCostConfig>("/ai-costs/config");
}

export function updateAiCostConfig(payload: AiCostConfigPayload) {
  return apiPut<AiCostConfig>("/ai-costs/config", payload);
}
