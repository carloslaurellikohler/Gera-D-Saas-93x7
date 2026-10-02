"""Camada de acesso a dados de trilhas de treinamento (LearningPath, Fase 5). Content e
LearningPath se relacionam muitos-para-muitos via LearningPathItem; sem relationship()
do SQLAlchemy — joins resolvidos explicitamente, mesmo estilo do resto do repositório
(ver MetricsRepository)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.constants import CriterionKey
from app.models.content import Content
from app.models.learning_path import LearningPath, LearningPathItem


class LearningPathRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self, learning_path: LearningPath, *, items: list[tuple[uuid.UUID, int]]
    ) -> LearningPath:
        self.db.add(learning_path)
        self.db.flush()
        for content_id, order_index in items:
            self.db.add(
                LearningPathItem(
                    learning_path_id=learning_path.id,
                    content_id=content_id,
                    order_index=order_index,
                )
            )
        self.db.commit()
        self.db.refresh(learning_path)
        return learning_path

    def get(self, learning_path_id: uuid.UUID) -> LearningPath | None:
        return self.db.get(LearningPath, learning_path_id)

    def update(
        self,
        learning_path_id: uuid.UUID,
        *,
        title: str,
        description: str | None,
        criterion_key: CriterionKey | None,
        estimated_duration_minutes: int | None,
        items: list[tuple[uuid.UUID, int]],
    ) -> LearningPath | None:
        learning_path = self.get(learning_path_id)
        if learning_path is None:
            return None

        learning_path.title = title
        learning_path.description = description
        learning_path.criterion_key = criterion_key
        learning_path.estimated_duration_minutes = estimated_duration_minutes

        self.db.execute(
            delete(LearningPathItem).where(LearningPathItem.learning_path_id == learning_path_id)
        )
        self.db.flush()
        for content_id, order_index in items:
            self.db.add(
                LearningPathItem(
                    learning_path_id=learning_path_id,
                    content_id=content_id,
                    order_index=order_index,
                )
            )
        self.db.commit()
        self.db.refresh(learning_path)
        return learning_path

    def list(self) -> list[LearningPath]:
        stmt = select(LearningPath).order_by(LearningPath.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def list_by_criterion_keys(self, keys: list[CriterionKey]) -> list[LearningPath]:
        if not keys:
            return []
        stmt = select(LearningPath).where(LearningPath.criterion_key.in_(keys))
        return list(self.db.execute(stmt).scalars().all())

    def list_items(self, learning_path_id: uuid.UUID) -> list[tuple[LearningPathItem, Content]]:
        stmt = (
            select(LearningPathItem, Content)
            .join(Content, Content.id == LearningPathItem.content_id)
            .where(LearningPathItem.learning_path_id == learning_path_id)
            .order_by(LearningPathItem.order_index)
        )
        return list(self.db.execute(stmt).all())

    def get_item(self, *, learning_path_id: uuid.UUID, item_id: uuid.UUID) -> LearningPathItem | None:
        stmt = select(LearningPathItem).where(
            LearningPathItem.id == item_id,
            LearningPathItem.learning_path_id == learning_path_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def count_items(self, learning_path_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(LearningPathItem)
            .where(LearningPathItem.learning_path_id == learning_path_id)
        )
        return self.db.execute(stmt).scalar_one()

    def delete(self, learning_path_id: uuid.UUID) -> None:
        learning_path = self.get(learning_path_id)
        if learning_path is not None:
            self.db.delete(learning_path)
            self.db.commit()
