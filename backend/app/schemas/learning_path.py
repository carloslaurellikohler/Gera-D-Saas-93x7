"""Schemas de request/response de trilhas de treinamento (LearningPath, Fase 5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.core.constants import CriterionKey
from app.schemas.content import ContentResponse


class LearningPathItemResponse(BaseModel):
    id: uuid.UUID
    content: ContentResponse
    order_index: int
    completed: bool = False


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


class EnrollmentResponse(BaseModel):
    learning_path_id: uuid.UUID
    enrolled_at: datetime


class EnrolledLearningPathSummary(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    criterion_key: CriterionKey | None
    estimated_duration_minutes: int | None
    item_count: int
    completed_count: int
    progress_percent: float
    is_completed: bool
    enrolled_at: datetime
    created_at: datetime


class CreateLearningPathItem(BaseModel):
    content_id: uuid.UUID
    order_index: int


class CreateLearningPathRequest(BaseModel):
    title: str
    description: str | None = None
    criterion_key: CriterionKey | None = None
    estimated_duration_minutes: int | None = None
    items: list[CreateLearningPathItem] = []
