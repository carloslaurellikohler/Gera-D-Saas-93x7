"""Camada de leitura para os indicadores agregados do dashboard (Fase 2). Só consulta
`analyses` — nunca grava, nunca toca engine/storage (ver DashboardService). As queries
devolvem tuplas cruas; formatação (pct, normalização de farol, trend) fica no service."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import Date, Float, Row, cast, func, select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import User

_BAND_LABEL = Analysis.analysis_result["overall_band_label"].astext
_OVERALL_SCORE = cast(Analysis.analysis_result["overall_score"].astext, Float)


class DashboardRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def count_by_status(
        self, *, owner_ids: Sequence[uuid.UUID] | None, since: date
    ) -> list[Row[tuple[AnalysisStatus, int]]]:
        stmt = (
            select(Analysis.status, func.count())
            .where(Analysis.created_at >= since)
            .group_by(Analysis.status)
        )
        if owner_ids is not None:
            stmt = stmt.where(Analysis.owner_id.in_(owner_ids))
        return list(self.db.execute(stmt).all())

    def count_by_band_label(
        self, *, owner_ids: Sequence[uuid.UUID] | None, since: date
    ) -> list[Row[tuple[str | None, int]]]:
        stmt = (
            select(_BAND_LABEL, func.count())
            .where(Analysis.status == AnalysisStatus.COMPLETED, Analysis.completed_at >= since)
            .group_by(_BAND_LABEL)
        )
        if owner_ids is not None:
            stmt = stmt.where(Analysis.owner_id.in_(owner_ids))
        return list(self.db.execute(stmt).all())

    def trend_by_week(
        self, *, owner_ids: Sequence[uuid.UUID] | None, since: date
    ) -> list[Row[tuple[date, int, float | None]]]:
        period_start = cast(func.date_trunc("week", Analysis.completed_at), Date)
        stmt = (
            select(period_start, func.count(), func.avg(_OVERALL_SCORE))
            .where(Analysis.status == AnalysisStatus.COMPLETED, Analysis.completed_at >= since)
            .group_by(period_start)
            .order_by(period_start)
        )
        if owner_ids is not None:
            stmt = stmt.where(Analysis.owner_id.in_(owner_ids))
        return list(self.db.execute(stmt).all())

    def completed_rows_by_owner(
        self, *, owner_ids: Sequence[uuid.UUID] | None, since: date
    ) -> list[Row[tuple[uuid.UUID, str, datetime, float | None, str | None]]]:
        """Linhas cruas (uma por análise concluída) para montar o quadro agrupado por
        colaborador dono da análise (Analysis.owner_id) — usado tanto pelo 'Quadro da
        equipe' do GESTOR (owner_ids=lista de subordinados) quanto pelo 'Quadro
        individual' do ADMIN (owner_ids=None, sem filtro, toda a organização)."""
        stmt = (
            select(
                Analysis.owner_id,
                User.name,
                Analysis.completed_at,
                _OVERALL_SCORE,
                _BAND_LABEL,
            )
            .join(User, User.id == Analysis.owner_id)
            .where(
                Analysis.status == AnalysisStatus.COMPLETED,
                Analysis.completed_at >= since,
            )
        )
        if owner_ids is not None:
            stmt = stmt.where(Analysis.owner_id.in_(owner_ids))
        return list(self.db.execute(stmt).all())
