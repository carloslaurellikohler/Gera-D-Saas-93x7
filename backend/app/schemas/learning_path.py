"""Schemas de request/response de trilhas de treinamento (LearningPath, Fase 5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.core.constants import CriterionKey
from app.schemas.content import ContentResponse


class LearningPathItemResponse(BaseModel):
    content: ContentResponse
    order_index: int


class LearningPathSummary(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    criterion_key: CriterionKey | None
    estimated_duration_minutes: int | None
    item_count: int
    created_at: datetime


class LearningPathDetail(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    criterion_key: CriterionKey | None
    estimated_duration_minutes: int | None
    created_at: datetime
    items: list[LearningPathItemResponse]


class CreateLearningPathItem(BaseModel):
    content_id: uuid.UUID
    order_index: int


class CreateLearningPathRequest(BaseModel):
    title: str
    description: str | None = None
    criterion_key: CriterionKey | None = None
    estimated_duration_minutes: int | None = None
    items: list[CreateLearningPathItem] = []
