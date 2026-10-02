"""Schemas de request/response de materiais de apoio (Content, Fase 5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import CriterionKey
from app.models.content import ContentKind


class ContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    criterion_key: CriterionKey | None
    kind: ContentKind
    file_path: str | None
    external_url: str | None
    uploaded_by_id: uuid.UUID | None
    created_at: datetime
