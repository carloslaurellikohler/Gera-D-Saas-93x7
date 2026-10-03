"""Schemas de request/response de metodologia/calibração versionada (Fase 7)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import CriterionKey
from app.models.methodology import FarolColor, MethodologyStatus


class MethodologyCategoryIn(BaseModel):
    key: CriterionKey
    label: str
    description: str
    order_index: int
    extra: dict[str, str] = Field(default_factory=dict)


class CalibratorIn(BaseModel):
    key: str
    label: str
    color: FarolColor
    min: float
    max: float
    order_index: int


class MethodologyDraftIn(BaseModel):
    calibration_version: str
    methodology_name: str
    project: str
    content: dict
    categories: list[MethodologyCategoryIn]
    calibrators: list[CalibratorIn]


class CreateMethodologyDraftRequest(BaseModel):
    from_id: uuid.UUID | None = None


class MethodologySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    calibration_version: str
    methodology_name: str
    status: MethodologyStatus
    created_at: datetime
    published_at: datetime | None
    archived_at: datetime | None


class MethodologyDetail(MethodologySummary):
    project: str
    content: dict
    categories: list[MethodologyCategoryIn]
    calibrators: list[CalibratorIn]
