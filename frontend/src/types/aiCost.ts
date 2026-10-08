// Espelho manual dos schemas pydantic de backend/app/schemas/ai_cost.py (FinAI).
// Custo chega como number (USD) — o backend converte Decimal→float só na borda HTTP.

export type AiCostPeriod = "7d" | "30d" | "90d" | "mtd";
export type AiCostTrendBucket = "day" | "week";
export type AiCostOperation = "CHAT" | "TRANSCRIPTION" | "EMBEDDING";
export type AiCostFeature = "ANALYSIS" | "ASSISTANT" | "INGESTION";
export type AiCostBudgetStatus = "unset" | "ok" | "warn" | "over";
// PRICED = custeado; NO_PRICE = sem vigência de preço cadastrada; NO_UNITS = unidade não
// medida (chamada que falhou, ffprobe indisponível).
export type AiCostStatus = "PRICED" | "NO_PRICE" | "NO_UNITS";

export interface AiCostKpis {
  total_usd: number;
  events: number;
  analyses_with_cost: number;
  avg_usd_per_analysis: number | null;
  assistant_messages: number;
  avg_usd_per_assistant_message: number | null;
  retry_usd: number;
  retry_events: number;
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  reasoning_tokens: number;
  audio_minutes: number;
  unpriced_events: number;
  no_units_events: number;
  failed_calls: number;
}

export interface AiCostBreakdownItem {
  key: string;
  label: string;
  total_usd: number;
  events: number;
  pct: string;
}

export interface AiCostTrendPoint {
  period_start: string;
  total_usd: number;
  events: number;
}

export interface AiCostStackedTrendPoint {
  period_start: string;
  analysis_usd: number;
  assistant_usd: number;
  ingestion_usd: number;
}

export interface AiCostUserRow {
  user_id: string | null;
  name: string;
  role: string | null;
  manager_name: string | null;
  total_usd: number;
  events: number;
  analyses: number;
}

export interface AiCostAnalysisRow {
  analysis_id: string | null;
  participant_name: string | null;
  owner_name: string | null;
  input_type: string | null;
  created_at: string | null;
  attempts: number;
  total_usd: number;
  events: number;
}

export interface AiCostBudget {
  month: string;
  amount_usd: number | null;
  spent_usd: number;
  pct: number | null;
  warn_threshold_pct: number;
  status: AiCostBudgetStatus;
  projected_month_end_usd: number | null;
}

export interface AiCostSummary {
  period: AiCostPeriod;
  trend_bucket: AiCostTrendBucket;
  tracking_started_at: string | null;
  usd_to_brl_rate: number | null;
  has_placeholder_prices: boolean;
  kpis: AiCostKpis;
  by_feature: AiCostBreakdownItem[];
  by_operation: AiCostBreakdownItem[];
  by_model: AiCostBreakdownItem[];
  by_stage: AiCostBreakdownItem[];
  trend: AiCostTrendPoint[];
  trend_by_feature: AiCostStackedTrendPoint[];
  top_users: AiCostUserRow[];
  top_analyses: AiCostAnalysisRow[];
  budget: AiCostBudget;
}

export interface AiUsageEvent {
  id: string;
  occurred_at: string;
  feature: string;
  operation: string;
  stage: string | null;
  stage_label: string;
  model: string;
  user_id: string | null;
  user_name: string | null;
  analysis_id: string | null;
  attempt: number;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  audio_seconds: number | null;
  cost_usd: number;
  cost_status: AiCostStatus;
  tokens_estimated: boolean;
  latency_ms: number | null;
  error_type: string | null;
}

export interface AiUsageEventPage {
  items: AiUsageEvent[];
  total: number;
  offset: number;
  limit: number;
  models: string[];
}

export interface AiUsageEventFilters {
  period?: AiCostPeriod;
  feature?: AiCostFeature;
  operation?: AiCostOperation;
  model?: string;
  offset?: number;
  limit?: number;
}

export interface AiModelPrice {
  id: string;
  model: string;
  operation: AiCostOperation;
  valid_from: string;
  input_usd_per_mtok: number | null;
  cached_input_usd_per_mtok: number | null;
  output_usd_per_mtok: number | null;
  usd_per_minute: number | null;
  is_placeholder: boolean;
  notes: string | null;
  is_current: boolean;
  updated_at: string | null;
}

export interface AiModelPricePayload {
  model: string;
  operation: AiCostOperation;
  valid_from: string;
  input_usd_per_mtok?: number | null;
  cached_input_usd_per_mtok?: number | null;
  output_usd_per_mtok?: number | null;
  usd_per_minute?: number | null;
  notes?: string | null;
}

export interface AiCostConfig {
  warn_threshold_pct: number;
  usd_to_brl_rate: number | null;
  usd_to_brl_rate_updated_at: string | null;
  current_month: string;
  current_month_budget_usd: number | null;
}

export interface AiCostConfigPayload {
  warn_threshold_pct: number;
  usd_to_brl_rate?: number | null;
  budget_month?: string | null;
  monthly_budget_usd?: number | null;
}

export interface AiRecalculateResult {
  updated: number;
}
