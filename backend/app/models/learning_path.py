"""Modelos de trilha de treinamento (LearningPath, Fase 5). Content e LearningPath se
relacionam muitos-para-muitos via LearningPathItem (com ordem), permitindo reaproveitar
o mesmo material em mais de uma trilha sem duplicar registro/arquivo. Sem
relationship() do SQLAlchemy — joins resolvidos explicitamente no repositório, mesmo
estilo do resto do módulo (ver models/analysis.py)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import CriterionKey
from app.db.base import Base


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    criterion_key: Mapped[CriterionKey | None] = mapped_column(
        Enum(CriterionKey, name="learning_path_criterion_key", native_enum=False, length=32)
    )
    # Override manual; se NULL, o frontend soma a duração estimada dos itens.
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


class LearningPathItem(Base):
    """Associação ordenada entre LearningPath e Content."""

    __tablename__ = "learning_path_items"
    __table_args__ = (
        UniqueConstraint("learning_path_id", "order_index", name="uq_learning_path_item_order"),
        UniqueConstraint("learning_path_id", "content_id", name="uq_learning_path_item_content"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    learning_path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # RESTRICT: impede apagar um material ainda referenciado por uma trilha sem
    # aviso — o service checa isso antes e devolve um 409 claro (ver ContentService.delete).
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
