"""Modelo de material de apoio da biblioteca (Content, Fase 5). Não relacionado à
engine — nunca importa gera_d_engine."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import CriterionKey
from app.db.base import Base


class ContentKind(str, enum.Enum):
    FILE = "FILE"
    LINK = "LINK"


class Content(Base):
    __tablename__ = "content"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    # Nullable: materiais "gerais" (onboarding, cultura de atendimento) não mapeiam a
    # um único critério.
    criterion_key: Mapped[CriterionKey | None] = mapped_column(
        Enum(CriterionKey, name="content_criterion_key", native_enum=False, length=32)
    )
    kind: Mapped[ContentKind] = mapped_column(
        Enum(ContentKind, name="content_kind", native_enum=False, length=16), nullable=False
    )

    # Exatamente um dos dois é preenchido, de acordo com `kind` — validado no service
    # (não via CHECK constraint, estilo do projeto).
    file_path: Mapped[str | None] = mapped_column(String(500))
    external_url: Mapped[str | None] = mapped_column(String(1000))

    # SET NULL (não CASCADE): remover o admin que subiu o material não deve apagar o
    # material em si — mesmo racional de analyses.owner_id.
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
