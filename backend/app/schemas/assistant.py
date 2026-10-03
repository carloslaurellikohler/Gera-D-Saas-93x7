"""Schemas de request/response do Assistente de IA (Fase 6)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class SendChatMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]
