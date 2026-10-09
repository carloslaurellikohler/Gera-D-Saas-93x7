from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Float, Row, cast, func, select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import User

_BAND_LABEL = Analysis.analysis_result["overall_band_label"].astext
_OVERALL_SCORE = cast(Analysis.analysis_result["overall_score"].astext, Float)


class AnalysisRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, analysis: Analysis) -> Analysis:
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def get(self, analysis_id: uuid.UUID) -> Analysis | None:
        return self.db.get(Analysis, analysis_id)

    def list(
        self,
        *,
        status: AnalysisStatus | None = None,
        owner_ids: Sequence[uuid.UUID] | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Analysis]:
        stmt = select(Analysis).order_by(Analysis.created_at.desc())
        if status is not None:
            stmt = stmt.where(Analysis.status == status)
        if owner_ids is not None:
            stmt = stmt.where(Analysis.owner_id.in_(owner_ids))
        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def list_with_owner(
        self,
        *,
        status: AnalysisStatus | None = None,
        owner_ids: Sequence[uuid.UUID] | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Row]:
        """Linhas cruas para a listagem do dashboard: traz o nome do dono (colaborador
        que fez a ligação) via LEFT JOIN — não INNER JOIN, porque owner_id é SET NULL e
        o ADMIN (owner_ids=None, sem filtro) precisa continuar vendo análises com dono
        removido — e a nota/farol extraídos do JSONB (None quando a análise ainda não
        está COMPLETED)."""
        stmt = (
            select(
                Analysis.id,
                Analysis.participant_name,
                Analysis.objective,
                Analysis.status,
                Analysis.created_at,
                Analysis.owner_id,
                User.name.label("owner_name"),
                Analysis.duration_seconds,
                _OVERALL_SCORE.label("overall_score"),
                _BAND_LABEL.label("band_label"),
            )
            .outerjoin(User, User.id == Analysis.owner_id)
            .order_by(Analysis.created_at.desc())
        )
        if status is not None:
            stmt = stmt.where(Analysis.status == status)
        if owner_ids is not None:
            stmt = stmt.where(Analysis.owner_id.in_(owner_ids))
        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.execute(stmt).all())

    def count(
        self,
        *,
        status: AnalysisStatus | None = None,
        owner_ids: Sequence[uuid.UUID] | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Analysis)
        if status is not None:
            stmt = stmt.where(Analysis.status == status)
        if owner_ids is not None:
            stmt = stmt.where(Analysis.owner_id.in_(owner_ids))
        return self.db.execute(stmt).scalar_one()

    def update(self, analysis_id: uuid.UUID, **fields: Any) -> Analysis:
        analysis = self.get(analysis_id)
        if analysis is None:
            raise ValueError(f"Analysis {analysis_id} not found")
        for key, value in fields.items():
            setattr(analysis, key, value)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def update_status(self, analysis_id: uuid.UUID, status: AnalysisStatus, **extra: Any) -> Analysis:
        return self.update(analysis_id, status=status, **extra)

    def count_today(self, *, owner_id: uuid.UUID, since: datetime) -> int:
        """Conta análises criadas hoje para este owner, qualquer status (inclusive
        FAILED — não há devolução de vaga na cota diária). Base do limite diário por
        colaborador."""
        stmt = (
            select(func.count())
            .select_from(Analysis)
            .where(Analysis.owner_id == owner_id, Analysis.created_at >= since)
        )
        return self.db.execute(stmt).scalar_one()

    def delete(self, analysis_id: uuid.UUID) -> None:
        analysis = self.get(analysis_id)
        if analysis is not None:
            self.db.delete(analysis)
            self.db.commit()
