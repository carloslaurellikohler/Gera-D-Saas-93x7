"""Chunks da metodologia 93x7® (docs/metodologia_93x7.pdf), com embedding pré-computado
para busca por similaridade em memória (ver AssistantService) — sem pgvector, corpus é
um único PDF pequeno e estático. Repovoada por completo via scripts/ingest_methodology.py
sempre que o PDF mudar; nunca editada via API HTTP."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MethodologyChunk(Base):
    __tablename__ = "methodology_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False, default="metodologia_93x7.pdf")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
