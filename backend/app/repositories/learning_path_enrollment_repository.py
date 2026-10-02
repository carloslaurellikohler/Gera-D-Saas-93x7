"""Camada de acesso a dados de inscrição/conclusão de trilha. Sem relationship() do
SQLAlchemy — joins explícitos, mesmo estilo de learning_path_repository.py."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.learning_path import LearningPath
from app.models.learning_path_enrollment import LearningPathEnrollment, LearningPathItemCompletion


class LearningPathEnrollmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_enrollment(
        self, *, user_id: uuid.UUID, learning_path_id: uuid.UUID
    ) -> LearningPathEnrollment | None:
        stmt = select(LearningPathEnrollment).where(
            LearningPathEnrollment.user_id == user_id,
            LearningPathEnrollment.learning_path_id == learning_path_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def enroll(self, *, user_id: uuid.UUID, learning_path_id: uuid.UUID) -> LearningPathEnrollment:
        """Idempotente: devolve a inscrição existente se já houver uma."""
        existing = self.get_enrollment(user_id=user_id, learning_path_id=learning_path_id)
        if existing is not None:
            return existing
        enrollment = LearningPathEnrollment(user_id=user_id, learning_path_id=learning_path_id)
        self.db.add(enrollment)
        self.db.commit()
        self.db.refresh(enrollment)
        return enrollment

    def list_enrolled_with_paths(
        self, user_id: uuid.UUID
    ) -> list[tuple[LearningPathEnrollment, LearningPath]]:
        stmt = (
            select(LearningPathEnrollment, LearningPath)
            .join(LearningPath, LearningPath.id == LearningPathEnrollment.learning_path_id)
            .where(LearningPathEnrollment.user_id == user_id)
            .order_by(LearningPathEnrollment.enrolled_at.desc())
        )
        return list(self.db.execute(stmt).all())

    def mark_item_complete(self, *, enrollment_id: uuid.UUID, learning_path_item_id: uuid.UUID) -> None:
        """Idempotente: não duplica se já concluído (UniqueConstraint também protege)."""
        stmt = select(LearningPathItemCompletion.id).where(
            LearningPathItemCompletion.enrollment_id == enrollment_id,
            LearningPathItemCompletion.learning_path_item_id == learning_path_item_id,
        )
        if self.db.execute(stmt).first() is not None:
            return
        self.db.add(
            LearningPathItemCompletion(
                enrollment_id=enrollment_id, learning_path_item_id=learning_path_item_id
            )
        )
        self.db.commit()

    def unmark_item_complete(self, *, enrollment_id: uuid.UUID, learning_path_item_id: uuid.UUID) -> None:
        """Idempotente: não falha se não havia conclusão (corrigir engano)."""
        stmt = select(LearningPathItemCompletion).where(
            LearningPathItemCompletion.enrollment_id == enrollment_id,
            LearningPathItemCompletion.learning_path_item_id == learning_path_item_id,
        )
        completion = self.db.execute(stmt).scalar_one_or_none()
        if completion is not None:
            self.db.delete(completion)
            self.db.commit()

    def completed_item_ids(self, enrollment_id: uuid.UUID) -> set[uuid.UUID]:
        stmt = select(LearningPathItemCompletion.learning_path_item_id).where(
            LearningPathItemCompletion.enrollment_id == enrollment_id
        )
        return set(self.db.execute(stmt).scalars().all())

    def count_completed(self, enrollment_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(LearningPathItemCompletion)
            .where(LearningPathItemCompletion.enrollment_id == enrollment_id)
        )
        return self.db.execute(stmt).scalar_one()
