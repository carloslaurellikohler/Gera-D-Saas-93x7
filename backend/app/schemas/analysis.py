"""Schemas de request/response da API. Nunca expõem o modelo SQLAlchemy diretamente
nem campos internos de plumbing com a engine (cs_id/cs_name/pb_id)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.analysis import AnalysisStatus


class AnalysisListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    participant_name: str
    objective: str
    status: AnalysisStatus
    created_at: datetime


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    participant_name: str
    objective: str
    objective_complement: str | None
    duration_seconds: int | None
    interaction_date: date | None
    input_type: str
    file_name: str | None
    status: AnalysisStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None


class AnalysisStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: AnalysisStatus
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime | None


class AnalysisQuotaResponse(BaseModel):
    owner_id: uuid.UUID
    used: int
    limit: int
    remaining: int
    exempt: bool


class AnalysisTranscriptionResponse(BaseModel):
    id: uuid.UUID
    transcription: dict[str, Any]


class AnalysisResultResponse(BaseModel):
    id: uuid.UUID
    analysis_result: dict[str, Any]
