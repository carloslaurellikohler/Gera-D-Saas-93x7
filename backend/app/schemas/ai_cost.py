"""Schemas de request/response do FinAI (custo de IA). Só ADMIN consome.

Custo trafega como `float` na borda HTTP (JSON não tem decimal), mas é `Decimal` em todo o
caminho interno — a conversão acontece só aqui, no último momento. Nunca fazer aritmética de
custo em float no backend.

`Period` é redeclarado localmente em vez de importado do dashboard, seguindo o precedente de
schemas/metrics.py: as janelas úteis para custo são outras (inclui "mtd", o mês corrente, e
não inclui 6m, que daria 180 pontos num gráfico diário).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Period = Literal["7d", "30d", "90d", "mtd"]
TrendBucket = Literal["day", "week"]
Operation = Literal["CHAT", "TRANSCRIPTION", "EMBEDDING"]
Feature = Literal["ANALYSIS", "ASSISTANT", "INGESTION"]
BudgetStatus = Literal["unset", "ok", "warn", "over"]


class AiCostKpis(BaseModel):
    total_usd: float
    events: int

    analyses_with_cost: int
    avg_usd_per_analysis: float | None
    assistant_messages: int
    avg_usd_per_assistant_message: float | None

    # Custo de retentativa: o pipeline inteiro reexecutado por falha transitória. Hoje
    # invisível; é um dos números mais acionáveis da tela.
    retry_usd: float
    retry_events: int

    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    reasoning_tokens: int
    audio_minutes: float

    # Os três contadores que mantêm a tela honesta sobre subcontagem.
    unpriced_events: int
    no_units_events: int
    failed_calls: int


class AiCostBreakdownItem(BaseModel):
    key: str
    label: str
    total_usd: float
    events: int
    pct: str  # já formatado pelo backend, como em FarolDistributionItem


class AiCostTrendPoint(BaseModel):
    period_start: date
    total_usd: float
    events: int


class AiCostStackedTrendPoint(BaseModel):
    """Um ponto da série empilhada por origem — mostra como a composição do gasto muda."""

    period_start: date
    analysis_usd: float
    assistant_usd: float
    ingestion_usd: float


class AiCostUserRow(BaseModel):
    user_id: str | None  # None = usuário removido (eventos ficam sem atribuição, não somem)
    name: str
    role: str | None
    manager_name: str | None
    total_usd: float
    events: int
    analyses: int


class AiCostAnalysisRow(BaseModel):
    analysis_id: str | None
    participant_name: str | None
    owner_name: str | None
    input_type: str | None
    created_at: datetime | None
    attempts: int
    total_usd: float
    events: int


class AiCostBudgetStatusResponse(BaseModel):
    month: date
    amount_usd: float | None
    spent_usd: float
    pct: float | None
    warn_threshold_pct: int
    status: BudgetStatus
    # Run-rate linear simples: gasto até agora projetado para o mês fechado.
    projected_month_end_usd: float | None


class AiCostSummaryResponse(BaseModel):
    period: Period
    trend_bucket: TrendBucket
    # Data do primeiro evento registrado. A tela declara isso porque não há backfill:
    # análises anteriores à feature simplesmente não têm dados de token.
    tracking_started_at: datetime | None
    # Taxa manual para exibir o equivalente em reais ao lado do dólar. Nenhum valor em BRL
    # é persistido — a conversão é só de apresentação.
    usd_to_brl_rate: float | None
    has_placeholder_prices: bool

    kpis: AiCostKpis
    by_feature: list[AiCostBreakdownItem]
    by_operation: list[AiCostBreakdownItem]
    by_model: list[AiCostBreakdownItem]
    by_stage: list[AiCostBreakdownItem]
    trend: list[AiCostTrendPoint]
    trend_by_feature: list[AiCostStackedTrendPoint]
    top_users: list[AiCostUserRow]
    top_analyses: list[AiCostAnalysisRow]
    budget: AiCostBudgetStatusResponse


class AiUsageEventItem(BaseModel):
    id: str
    occurred_at: datetime
    feature: str
    operation: str
    stage: str | None
    stage_label: str
    model: str
    user_id: str | None
    user_name: str | None
    analysis_id: str | None
    attempt: int
    calls: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    audio_seconds: float | None
    cost_usd: float
    cost_status: str
    tokens_estimated: bool
    latency_ms: int | None
    error_type: str | None


class AiUsageEventPage(BaseModel):
    items: list[AiUsageEventItem]
    # COUNT real, não len(items): numa tela financeira saber quantos eventos existem de
    # fato é o ponto (desvio deliberado de routes/analyses.py).
    total: int
    offset: int
    limit: int
    models: list[str]  # alimenta o filtro de modelo sem o frontend adivinhar nomes


class AiModelPriceResponse(BaseModel):
    id: str
    model: str
    operation: str
    valid_from: date
    input_usd_per_mtok: float | None
    cached_input_usd_per_mtok: float | None
    output_usd_per_mtok: float | None
    usd_per_minute: float | None
    is_placeholder: bool
    notes: str | None
    is_current: bool  # se é a vigência em efeito hoje para (model, operation)
    updated_at: datetime | None


class AiModelPriceIn(BaseModel):
    model: str = Field(min_length=1, max_length=64)
    operation: Operation
    valid_from: date
    # Preços por 1 milhão de tokens — é como a OpenAI publica, então o ADMIN digita o
    # número direto da página de preços.
    input_usd_per_mtok: float | None = Field(default=None, ge=0)
    cached_input_usd_per_mtok: float | None = Field(default=None, ge=0)
    output_usd_per_mtok: float | None = Field(default=None, ge=0)
    usd_per_minute: float | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=500)


class AiCostConfigResponse(BaseModel):
    warn_threshold_pct: int
    usd_to_brl_rate: float | None
    usd_to_brl_rate_updated_at: datetime | None
    current_month: date
    current_month_budget_usd: float | None


class AiCostConfigIn(BaseModel):
    warn_threshold_pct: int = Field(ge=1, le=100)
    usd_to_brl_rate: float | None = Field(default=None, gt=0)
    # Mês do orçamento (qualquer dia; o service normaliza para o dia 1). None usa o mês
    # corrente. Versionado por mês para não reescrever o julgamento de meses fechados.
    budget_month: date | None = None
    monthly_budget_usd: float | None = Field(default=None, ge=0)


class AiRecalculateResponse(BaseModel):
    updated: int
