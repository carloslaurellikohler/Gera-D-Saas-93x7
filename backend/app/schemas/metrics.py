"""Schemas de resposta das métricas de evolução (Fase 4) — radar dos 6 critérios
comportamentais e tendência temporal da nota geral/pilares, agregados a partir de
analyses.analysis_result (JSONB). Só leitura; mesmo contrato de escopo do dashboard
(Fase 2): escopo sempre derivado do usuário autenticado."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

Period = Literal["30d", "90d", "6m"]


class CriterionRadarPoint(BaseModel):
    key: str
    label: str
    score: float | None
    previous_score: float | None
    sample_size: int


class MetricsTrendPoint(BaseModel):
    period_start: date
    count: int
    avg_overall_score: float | None
    avg_pilar_93: float | None
    avg_pilar_7: float | None


class MetricsEvolutionResponse(BaseModel):
    period: Period
    radar: list[CriterionRadarPoint]
    trend: list[MetricsTrendPoint]
