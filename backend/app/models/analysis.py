"""Modelo de domínio da análise. Mapeia para/de gera_d_engine apenas na fronteira de
engine_integration/mappers.py — este módulo nunca importa gera_d_engine."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisStatus(str, enum.Enum):
    CREATED = "CREATED"
    UPLOADED = "UPLOADED"
    TRANSCRIBING = "TRANSCRIBING"
    TRANSCRIBED = "TRANSCRIBED"
    ANALYZING = "ANALYZING"
    GENERATING_REPORTS = "GENERATING_REPORTS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Metadados fornecidos pelo usuário na criação
    participant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(String(64), nullable=False)
    objective_complement: Mapped[str | None] = mapped_column(String(500))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    interaction_date: Mapped[date | None] = mapped_column(Date)

    # Arquivo de entrada
    input_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(500))

    # Estado do pipeline
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status", native_enum=False, length=32),
        nullable=False,
        default=AnalysisStatus.CREATED,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    # Dono da análise (colaborador avaliado — cujas métricas/dashboard contam o
    # registro). Nullable: análises criadas antes da Fase 3 ficam órfãs (SET NULL se
    # o usuário for removido), nunca com uma proveniência fictícia — toda análise nova
    # sempre recebe um owner_id real.
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    # Quem de fato fez o upload (pode ser o próprio dono, ou o Gestor da equipe dele
    # subindo em nome de um colaborador). Distinto de owner_id desde a Fase de
    # hierarquia Gestor/Colaborador — antes disso, criador e dono eram sempre a mesma
    # pessoa (ver migration c3f5e9a72d64).
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    # Identidade da interação para a engine (ver mappers.build_input_metadata)
    cs_id: Mapped[str | None] = mapped_column(String(64))
    cs_name: Mapped[str | None] = mapped_column(String(255))
    pb_id: Mapped[str | None] = mapped_column(String(64))
    interaction_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Versão de metodologia usada para gerar o resultado (Fase 7) — RESTRICT: nunca
    # apagar uma versão referenciada por uma análise existente. Nullable: análises
    # pré-Fase-7 ficam órfãs aqui (a única pista histórica delas é a string
    # calibration_version dentro de analysis_result), sem backfill artificial.
    methodology_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("methodologies.id", ondelete="RESTRICT"), index=True
    )

    # Resultados produzidos pela engine
    transcription: Mapped[dict | None] = mapped_column(JSONB)
    analysis_result: Mapped[dict | None] = mapped_column(JSONB)
    executive_report_path: Mapped[str | None] = mapped_column(String(500))
    detailed_report_path: Mapped[str | None] = mapped_column(String(500))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
