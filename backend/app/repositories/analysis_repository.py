from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis, AnalysisStatus


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

    def delete(self, analysis_id: uuid.UUID) -> None:
        analysis = self.get(analysis_id)
        if analysis is not None:
            self.db.delete(analysis)
            self.db.commit()
