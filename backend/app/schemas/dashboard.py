"""Schemas de resposta do dashboard agregado (Fase 2). Só leitura — nunca expõem
campos de plumbing com a engine (cs_id/cs_name/pb_id), só o necessário para os
indicadores agregados."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

Period = Literal["30d", "90d", "6m"]


class VolumeByStatus(BaseModel):
    status: str
    count: int


class FarolDistributionItem(BaseModel):
    label: str
    level: str
    count: int
    pct: str


class TrendPoint(BaseModel):
    period_start: date
    count: int
    avg_score: float | None


class ProfessionalBoardRow(BaseModel):
    # PB avaliado (participant_name da Analysis) — não o usuário/CS dono do registro.
    pb_id: str
    name: str
    count: int
    avg_score: float | None
    level: str | None
    trend: Literal["up", "down", "flat"] | None


class TeamBoardRow(BaseModel):
    # Colaborador da equipe do GESTOR (Analysis.owner_id) — mesmos campos de
    # ProfessionalBoardRow, trocando o agrupamento de PB avaliado para usuário dono.
    user_id: str
    name: str
    count: int
    avg_score: float | None
    level: str | None
    trend: Literal["up", "down", "flat"] | None


class DashboardStatsResponse(BaseModel):
    period: Period
    volume_by_status: list[VolumeByStatus]
    farol_distribution: list[FarolDistributionItem]
    trend: list[TrendPoint]
    board: list[ProfessionalBoardRow] | None = None
    team_board: list[TeamBoardRow] | None = None
