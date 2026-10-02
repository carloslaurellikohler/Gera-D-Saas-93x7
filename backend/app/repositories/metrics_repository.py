"""Camada de leitura das métricas de evolução (Fase 4). Só consulta `analyses`; a
agregação (médias por critério, buckets semanais) é feita em Python no
MetricsService — ver precedente DashboardRepository.completed_rows_by_participant,
já que iterar scores_by_criterion (array JSONB) em SQL puro exigiria
jsonb_array_elements e ficaria fora do estilo do resto do repositório."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis, AnalysisStatus


class MetricsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def completed_rows(
        self, *, user_id: uuid.UUID | None, since: date
    ) -> list[Row[tuple[datetime, dict]]]:
        """Uma linha por análise concluída com completed_at >= since. analysis_result
        vem inteiro (dict) — a extração de scores_by_criterion/pilares/overall_score
        é feita no service."""
        stmt = select(Analysis.completed_at, Analysis.analysis_result).where(
            Analysis.status == AnalysisStatus.COMPLETED,
            Analysis.completed_at >= since,
            Analysis.analysis_result.is_not(None),
        )
        if user_id is not None:
            stmt = stmt.where(Analysis.user_id == user_id)
        return list(self.db.execute(stmt).all())
