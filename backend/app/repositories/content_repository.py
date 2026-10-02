from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import CriterionKey
from app.models.content import Content
from app.models.learning_path import LearningPathItem


class ContentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, content: Content) -> Content:
        self.db.add(content)
        self.db.commit()
        self.db.refresh(content)
        return content

    def get(self, content_id: uuid.UUID) -> Content | None:
        return self.db.get(Content, content_id)

    def list(self, *, criterion_key: CriterionKey | None = None) -> list[Content]:
        stmt = select(Content).order_by(Content.created_at.desc())
        if criterion_key is not None:
            stmt = stmt.where(Content.criterion_key == criterion_key)
        return list(self.db.execute(stmt).scalars().all())

    def is_referenced_by_learning_path(self, content_id: uuid.UUID) -> bool:
        stmt = select(LearningPathItem.id).where(LearningPathItem.content_id == content_id).limit(1)
        return self.db.execute(stmt).first() is not None

    def delete(self, content_id: uuid.UUID) -> None:
        content = self.get(content_id)
        if content is not None:
            self.db.delete(content)
            self.db.commit()
